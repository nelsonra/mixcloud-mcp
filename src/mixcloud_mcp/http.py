"""Entry point for HTTP (Streamable HTTP) transport — used for hosted/remote clients."""
import os
import uvicorn
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv()

from mixcloud_mcp.server import mcp  # noqa: E402


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Rejects requests that don't carry a valid Bearer token.

    If MCP_API_KEY is not set the server starts without auth — useful for
    local testing, but never run this way in production.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/ping":
            return JSONResponse({"status": "ok"})

        api_key = os.getenv("MCP_API_KEY")

        if api_key:
            auth = request.headers.get("Authorization", "")
            if auth != f"Bearer {api_key}":
                return JSONResponse(
                    {"error": "Unauthorized", "message": "Valid Bearer token required"},
                    status_code=401,
                )

        return await call_next(request)


def run() -> None:
    port = int(os.getenv("MCP_PORT", "8000"))

    app = mcp.http_app(transport="streamable-http")
    app.add_middleware(BearerAuthMiddleware)

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    run()
