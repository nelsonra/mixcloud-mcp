import json
import os
from pathlib import Path
from urllib.parse import urlparse

from fastmcp import FastMCP
from fastmcp.apps import AppConfig, ResourceCSP
from fastmcp.server.dependencies import get_access_token

RESOURCE_URI = "ui://mixcloud/upload-cloudcast.html"

# src/mixcloud_mcp/static/ is included in the installed package by hatchling.
# parents[2] navigates: tracks/ → tools/ → mixcloud_mcp/
HTML_PATH = Path(__file__).parents[2] / "static" / "mcp-app.html"


def _upload_url() -> str:
    # MCP_PUBLIC_URL wins in all modes (remote hosting, or explicit override).
    if public_url := os.getenv("MCP_PUBLIC_URL"):
        return f"{public_url.rstrip('/')}/upload"
    # UPLOAD_PORT → sidecar (stdio mode). MCP_PORT → HTTP server mode.
    port = os.getenv("UPLOAD_PORT") or os.getenv("MCP_PORT", "8000")
    return f"http://localhost:{port}/upload"


def register(mcp: FastMCP) -> None:
    upload_url = _upload_url()

    # CSP needs the *origin* (scheme + host + port), not the full path.
    # The browser sandbox blocks fetch() to any origin not in this list.
    parsed = urlparse(upload_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    @mcp.tool(app=AppConfig(resource_uri=RESOURCE_URI))
    async def upload_cloudcast(name: str | None = None) -> str:
        """Upload a recording to Mixcloud. Opens a file picker UI.

        Args:
            name: Optional mix or show title to pre-fill in the upload form.
        """
        access = get_access_token()
        upload_token = access.token if access else os.getenv("MIXCLOUD_ACCESS_TOKEN")

        if not upload_token:
            public_url = os.getenv("MCP_PUBLIC_URL", "http://localhost:8000").rstrip("/")
            auth_url = f"{public_url}/oauth/authorize"
            return json.dumps({
                "error": "not_authenticated",
                "message": f"Not authenticated with Mixcloud. Visit {auth_url} to connect your account, then try again.",
                "auth_url": auth_url,
            })

        return json.dumps({
            "upload_url": upload_url,
            "upload_token": upload_token,
            "name": name,
        })

    @mcp.resource(
        RESOURCE_URI,
        app=AppConfig(csp=ResourceCSP(connect_domains=[origin])),
    )
    def upload_cloudcast_ui() -> str:
        return HTML_PATH.read_text(encoding="utf-8")
