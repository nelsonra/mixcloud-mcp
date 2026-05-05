"""Entry point for HTTP (Streamable HTTP) transport — used for hosted/remote clients."""
import os
import sys
import time
import urllib.parse
from collections import defaultdict

import httpx
import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

from mixcloud_mcp.auth import MIXCLOUD_AUTH_URL, MIXCLOUD_TOKEN_URL
from mixcloud_mcp.routes.upload import route as upload_route
from mixcloud_mcp.server import mcp

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

        # These routes must be reachable without a bearer token:
        # /upload — client sends the Mixcloud token; Mixcloud rejects if invalid.
        # /oauth/* — browser redirects from Mixcloud can't inject headers.
        # /.well-known/* and /register — MCP protocol discovery; clients probe these
        #   before they know how to authenticate. Must return 404 (not 401) if unused.
        if (
            path == "/upload"
            or path.startswith("/oauth/")
            or path.startswith("/.well-known/")
            or path == "/register"
        ):
            await self.app(scope, receive, send)
            return

        disable_auth = os.getenv("DISABLE_AUTH", "").lower() == "true"
        api_key = os.getenv("MCP_API_KEY")

        if not disable_auth and api_key:
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


def _build_oauth_routes(client_id: str, client_secret: str, public_url: str) -> list:
    """Build /oauth/authorize and /oauth/callback routes.

    Same pattern as the sidecar: the server authenticates to Mixcloud once,
    stores the token in os.environ, and all tools share it.
    """
    redirect_uri = f"{public_url.rstrip('/')}/oauth/callback"

    async def authorize(_request: Request) -> RedirectResponse:
        params = urllib.parse.urlencode({
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
        })
        return RedirectResponse(url=f"{MIXCLOUD_AUTH_URL}?{params}")

    async def callback(request: Request) -> HTMLResponse:
        code = request.query_params.get("code")
        error = request.query_params.get("error")

        if error or not code:
            msg = error or "No authorization code received"
            return HTMLResponse(
                f"<html><body><p>Authorization failed: {msg}</p></body></html>",
                status_code=400,
            )

        try:
            resp = httpx.get(MIXCLOUD_TOKEN_URL, params={
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            })
            resp.raise_for_status()

            try:
                data = resp.json()
            except Exception:
                from urllib.parse import parse_qsl
                data = dict(parse_qsl(resp.text))

            token = data.get("access_token")
            if not token:
                return HTMLResponse(
                    f"<html><body><p>Unexpected response: {resp.text}</p></body></html>",
                    status_code=500,
                )

            os.environ["MIXCLOUD_ACCESS_TOKEN"] = token
            print("[http] Mixcloud token stored — upload tool is now authenticated.", file=sys.stderr)
            return HTMLResponse(
                "<html><body>"
                "<h2>Mixcloud connected</h2>"
                "<p>Authorization successful — you can close this tab.</p>"
                "</body></html>"
            )

        except Exception as exc:
            return HTMLResponse(
                f"<html><body><p>Token exchange failed: {exc}</p></body></html>",
                status_code=500,
            )

    return [
        Route("/oauth/authorize", authorize, methods=["GET"]),
        Route("/oauth/callback", callback, methods=["GET"]),
    ]


def run() -> None:
    load_dotenv()
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

    # OAuth routes let the server authenticate to Mixcloud (like the stdio sidecar).
    # These are independent of DISABLE_AUTH — DISABLE_AUTH controls MCP endpoint access,
    # not whether the server can authenticate to Mixcloud for the upload tool.
    oauth_routes = []
    if oauth_configured:
        oauth_routes = _build_oauth_routes(client_id, client_secret, public_url)

    mcp_starlette = mcp.http_app(transport="streamable-http")

    app = Starlette(
        routes=[
            upload_route,
            *oauth_routes,
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
    if disable_auth:
        print(f"Endpoint: POST http://0.0.0.0:{port}/mcp  (no auth — dev only)", file=sys.stderr)
        print("WARNING: Auth is disabled — do not run this way in production", file=sys.stderr)
    elif api_key:
        print(f"Endpoint: POST http://0.0.0.0:{port}/mcp  (Authorization: Bearer <MCP_API_KEY>)",
              file=sys.stderr)
    if oauth_configured:
        print(f"Mixcloud auth: GET {public_url}/oauth/authorize", file=sys.stderr)
        if os.getenv("MIXCLOUD_ACCESS_TOKEN"):
            print("[http] Mixcloud access token loaded from env — upload tool ready.", file=sys.stderr)
        else:
            print(f"[http] No Mixcloud token — visit {public_url}/oauth/authorize to enable uploads.",
                  file=sys.stderr)
    print(f"Upload:   POST http://0.0.0.0:{port}/upload", file=sys.stderr)

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    run()
