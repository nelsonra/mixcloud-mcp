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

        # Auth — skip if DISABLE_AUTH=true or MCP_API_KEY not set
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


def run() -> None:
    port = int(os.getenv("MCP_PORT", "8000"))
    disable_auth = os.getenv("DISABLE_AUTH", "").lower() == "true"
    api_key = os.getenv("MCP_API_KEY")

    if not disable_auth and not api_key:
        print("ERROR: MCP_API_KEY is required. Generate one with: mixcloud-mcp-keygen", file=sys.stderr)
        print("       Or set DISABLE_AUTH=true to run without auth (local dev only)", file=sys.stderr)
        sys.exit(1)

    mcp_starlette = mcp.http_app(transport="streamable-http")

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
    print(f"Endpoint: POST http://0.0.0.0:{port}/mcp  (Authorization: Bearer <MCP_API_KEY>)", file=sys.stderr)
    print(f"Upload:   POST http://0.0.0.0:{port}/upload", file=sys.stderr)
    if disable_auth:
        print("WARNING: Auth is disabled — do not run this way in production", file=sys.stderr)

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    run()
