import json
import os
from pathlib import Path
from urllib.parse import urlparse

from fastmcp import FastMCP
from fastmcp.apps import AppConfig, ResourceCSP
from fastmcp.server.dependencies import get_access_token

from mixcloud_mcp import upload_log

RESOURCE_URI = "ui://mixcloud/upload-cloudcast.html"

# Walk up from src/mixcloud_mcp/tools/tracks/ to the project root, then into mcp-app/dist/.
HTML_PATH = Path(__file__).parents[4] / "mcp-app" / "dist" / "mcp-app.html"


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
        # HTTP OAuth mode: get_access_token().token is the Mixcloud token stored
        # by the proxy. All other modes (stdio sidecar, plain MCP_API_KEY) fall
        # back to MIXCLOUD_ACCESS_TOKEN from env — the sidecar writes it there
        # after the OAuth callback completes.
        access = get_access_token()
        upload_token = access.token if access else os.getenv("MIXCLOUD_ACCESS_TOKEN")

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
