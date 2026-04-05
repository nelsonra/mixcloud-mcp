"""Entry point for HTTP (Streamable HTTP) transport — used for hosted/remote clients."""
import os
import sys
import time
import uvicorn
from collections import defaultdict
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv()

from mixcloud_mcp.server import mcp  # noqa: E402

# In-memory rate limit store: {ip: [timestamp, ...]}
_request_log: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 120       # max requests
RATE_WINDOW = 60.0     # per 60 seconds


class McpMiddleware(BaseHTTPMiddleware):
    """Handles auth, rate limiting, and health check for all requests."""

    async def dispatch(self, request: Request, call_next):
        # Health check — no auth or rate limiting required
        if request.url.path == "/ping":
            return JSONResponse({"status": "ok"})

        # Rate limiting — applies to all other routes
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - RATE_WINDOW
        _request_log[ip] = [t for t in _request_log[ip] if t > window_start]

        if len(_request_log[ip]) >= RATE_LIMIT:
            return JSONResponse(
                {"error": "Too Many Requests", "message": f"Max {RATE_LIMIT} requests per minute"},
                status_code=429,
            )
        _request_log[ip].append(now)

        # Auth — skip if DISABLE_AUTH=true or MCP_API_KEY not set
        disable_auth = os.getenv("DISABLE_AUTH", "").lower() == "true"
        api_key = os.getenv("MCP_API_KEY")

        if not disable_auth and api_key:
            auth = request.headers.get("Authorization", "")
            if auth != f"Bearer {api_key}":
                return JSONResponse(
                    {"error": "Unauthorized", "message": "Valid Bearer token required"},
                    status_code=401,
                )

        return await call_next(request)


def run() -> None:
    port = int(os.getenv("MCP_PORT", "8000"))
    disable_auth = os.getenv("DISABLE_AUTH", "").lower() == "true"
    api_key = os.getenv("MCP_API_KEY")

    if not disable_auth and not api_key:
        print("ERROR: MCP_API_KEY is required. Generate one with: mixcloud-mcp-keygen", file=sys.stderr)
        print("       Or set DISABLE_AUTH=true to run without auth (local dev only)", file=sys.stderr)
        sys.exit(1)

    app = mcp.http_app(transport="streamable-http")
    app.add_middleware(McpMiddleware)

    print(f"Mixcloud MCP HTTP server starting on port {port}", file=sys.stderr)
    print(f"Health:   GET  http://0.0.0.0:{port}/ping", file=sys.stderr)
    print(f"Endpoint: POST http://0.0.0.0:{port}/mcp  (Authorization: Bearer <MCP_API_KEY>)", file=sys.stderr)
    if disable_auth:
        print("WARNING: Auth is disabled — do not run this way in production", file=sys.stderr)

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    run()
