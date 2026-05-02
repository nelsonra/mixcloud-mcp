"""Sidecar HTTP server for stdio transport.

Runs as a background daemon thread alongside the stdio MCP process. Provides:
  - POST /upload   — forwards multipart uploads to Mixcloud (same route as HTTP mode)
  - GET  /oauth/authorize  — redirects to Mixcloud's OAuth page
  - GET  /oauth/callback   — exchanges the code, writes token to .env + os.environ

Why a sidecar instead of the full OAuthProxy:
  OAuthProxy is designed for MCP clients authenticating *to* the server over HTTP.
  In stdio mode there are no HTTP MCP clients — Claude Desktop connects via stdin/stdout.
  The OAuth flow here is for the server itself to obtain a Mixcloud API token, which is
  then stored in .env and read by tools as MIXCLOUD_ACCESS_TOKEN. See ADR 002.
"""

import os
import sys
import threading
import urllib.parse
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.routing import Route

from mixcloud_mcp.auth import MIXCLOUD_AUTH_URL, MIXCLOUD_TOKEN_URL
from mixcloud_mcp.routes.upload import route as upload_route

SIDECAR_PORT_DEFAULT = 4000


def _find_env_file() -> Path:
    path = Path.cwd()
    while path != path.parent:
        candidate = path / ".env"
        if candidate.exists():
            return candidate
        path = path.parent
    return Path.cwd() / ".env"


def _persist_token(token: str) -> None:
    from dotenv import set_key
    env_file = _find_env_file()
    set_key(str(env_file), "MIXCLOUD_ACCESS_TOKEN", token, quote_mode="never")
    os.environ["MIXCLOUD_ACCESS_TOKEN"] = token
    print("[sidecar] Mixcloud token saved — tools are now authenticated.", file=sys.stderr)


def _build_app(port: int) -> Starlette:
    client_id = os.getenv("MIXCLOUD_CLIENT_ID", "")
    client_secret = os.getenv("MIXCLOUD_CLIENT_SECRET", "")
    redirect_uri = f"http://localhost:{port}/oauth/callback"

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

        import httpx
        from urllib.parse import parse_qsl

        try:
            resp = httpx.get(MIXCLOUD_TOKEN_URL, params={
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            })
            resp.raise_for_status()

            # Mixcloud returns URL-encoded text (access_token=xxx), not JSON.
            try:
                data = resp.json()
            except Exception:
                data = dict(parse_qsl(resp.text))

            token = data.get("access_token")
            if not token:
                return HTMLResponse(
                    f"<html><body><p>Unexpected response: {resp.text}</p></body></html>",
                    status_code=500,
                )

            _persist_token(token)
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

    app = Starlette(routes=[
        upload_route,
        Route("/oauth/authorize", authorize, methods=["GET"]),
        Route("/oauth/callback", callback, methods=["GET"]),
    ])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


def start(port: int | None = None) -> int:
    """Start the sidecar in a background daemon thread. Returns the port used."""
    port = port or int(os.getenv("UPLOAD_PORT", str(SIDECAR_PORT_DEFAULT)))
    app = _build_app(port)

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    return port
