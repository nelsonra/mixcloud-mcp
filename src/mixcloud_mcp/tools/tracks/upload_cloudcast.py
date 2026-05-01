import json
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastmcp import FastMCP
from fastmcp.apps import AppConfig, ResourceCSP

from mixcloud_mcp.api.client import mixcloud_post_multipart
from mixcloud_mcp import upload_log

RESOURCE_URI = "ui://mixcloud/upload-cloudcast.html"

# Walk up from src/mixcloud_mcp/tools/tracks/ to the project root, then into mcp-app/dist/.
HTML_PATH = Path(__file__).parents[4] / "mcp-app" / "dist" / "mcp-app.html"


def _upload_url() -> str:
    port = os.getenv("MCP_PORT", "8000")
    public_url = os.getenv("MCP_PUBLIC_URL", f"http://localhost:{port}")
    return f"{public_url.rstrip('/')}/upload"


def register(mcp: FastMCP) -> None:
    upload_url = _upload_url()
    upload_token = os.getenv("MCP_API_KEY")

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
