"""Entry point for HTTP (Streamable HTTP) transport — used for hosted/remote clients."""
import os
import sys
import time
import uvicorn
from collections import defaultdict
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount
from starlette.types import ASGIApp, Receive, Scope, Send

load_dotenv()

from mixcloud_mcp.server import mcp  # noqa: E402
from mixcloud_mcp.routes.upload import route as upload_route  # noqa: E402
from mixcloud_mcp.auth import (  # noqa: E402
    MixcloudOAuthProxy,
    MixcloudTokenVerifier,
    MIXCLOUD_AUTH_URL,
    MIXCLOUD_TOKEN_URL,
)

# In-memory rate limit store: {ip: [timestamp, ...]}
_request_log: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 120       # max requests
RATE_WINDOW = 60.0     # per 60 seconds


class McpMiddleware:
    """Handles auth, rate limiting, and health check for all requests.

    Pure ASGI middleware (not BaseHTTPMiddleware) so it doesn't buffer streaming
    responses — required for FastMCP's streamable-http SSE transport to work.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")

        # Health check — no auth or rate limiting required
        if path == "/ping":
            response = JSONResponse({"status": "ok"})
            await response(scope, receive, send)
            return

        # Rate limiting — applies to all other routes
        client = scope.get("client")
        ip = client[0] if client else "unknown"
        now = time.time()
        window_start = now - RATE_WINDOW
        _request_log[ip] = [t for t in _request_log[ip] if t > window_start]

        if len(_request_log[ip]) >= RATE_LIMIT:
            response = JSONResponse(
                {"error": "Too Many Requests", "message": f"Max {RATE_LIMIT} requests per minute"},
                status_code=429,
            )
            await response(scope, receive, send)
            return
        _request_log[ip].append(now)

        # /upload has its own auth: the client sends the Mixcloud token as Bearer.
        # Mixcloud's API rejects it if invalid, so no separate check is needed here.
        if path == "/upload":
            await self.app(scope, receive, send)
            return

        # Auth — skip if DISABLE_AUTH=true or MCP_API_KEY not set.
        # When OAuthProxy is configured, the MCP routes are protected by OAuth
        # at the FastMCP layer; MCP_API_KEY is only used when OAuth is not set up.
        disable_auth = os.getenv("DISABLE_AUTH", "").lower() == "true"
        api_key = os.getenv("MCP_API_KEY")
        oauth_configured = bool(
            os.getenv("MIXCLOUD_CLIENT_ID") and os.getenv("MIXCLOUD_CLIENT_SECRET")
        )

        if not disable_auth and api_key and not oauth_configured:
            headers = {k.lower(): v for k, v in scope.get("headers", [])}
            auth = headers.get(b"authorization", b"").decode()
            if auth != f"Bearer {api_key}":
                response = JSONResponse(
                    {"error": "Unauthorized", "message": "Valid Bearer token required"},
                    status_code=401,
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)


def run() -> None:
    port = int(os.getenv("MCP_PORT", "8000"))
    disable_auth = os.getenv("DISABLE_AUTH", "").lower() == "true"
    api_key = os.getenv("MCP_API_KEY")
    client_id = os.getenv("MIXCLOUD_CLIENT_ID")
    client_secret = os.getenv("MIXCLOUD_CLIENT_SECRET")
    public_url = os.getenv("MCP_PUBLIC_URL", f"http://localhost:{port}")

    oauth_configured = bool(client_id and client_secret)

    if not disable_auth and not api_key and not oauth_configured:
        print("ERROR: Authentication is required. Either:", file=sys.stderr)
        print("  - Set MIXCLOUD_CLIENT_ID + MIXCLOUD_CLIENT_SECRET for OAuth", file=sys.stderr)
        print("  - Set MCP_API_KEY for simple Bearer token auth", file=sys.stderr)
        print("  - Set DISABLE_AUTH=true for local dev only", file=sys.stderr)
        sys.exit(1)

    auth = None
    if oauth_configured:
        auth = MixcloudOAuthProxy(
            upstream_authorization_endpoint=MIXCLOUD_AUTH_URL,
            upstream_token_endpoint=MIXCLOUD_TOKEN_URL,
            upstream_client_id=client_id,
            upstream_client_secret=client_secret,
            token_verifier=MixcloudTokenVerifier(),
            base_url=public_url,
            forward_pkce=False,
            extra_token_params={"method": "GET"},
            require_authorization_consent=False,
            fallback_access_token_expiry_seconds=365 * 24 * 3600,
        )

    mcp_starlette = mcp.http_app(transport="streamable-http", auth=auth)

    app = Starlette(
        routes=[
            upload_route,
            Mount("/", app=mcp_starlette),
        ],
        lifespan=mcp_starlette.lifespan,
    )
    cors_origin = os.getenv("CORS_ORIGIN", "*")
    app.add_middleware(McpMiddleware)
    # CORSMiddleware is added last so it wraps outermost — it must handle the
    # browser's OPTIONS preflight before auth runs, otherwise preflight gets a 401.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[cors_origin],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    print(f"Mixcloud MCP HTTP server starting on port {port}", file=sys.stderr)
    print(f"Health:   GET  http://0.0.0.0:{port}/ping", file=sys.stderr)
    if oauth_configured:
        print(f"Endpoint: POST {public_url}/mcp  (OAuth — authenticate via {public_url}/authorize)", file=sys.stderr)
    else:
        print(f"Endpoint: POST http://0.0.0.0:{port}/mcp  (Authorization: Bearer <MCP_API_KEY>)", file=sys.stderr)
    print(f"Upload:   POST http://0.0.0.0:{port}/upload", file=sys.stderr)
    if disable_auth:
        print("WARNING: Auth is disabled — do not run this way in production", file=sys.stderr)

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    run()
