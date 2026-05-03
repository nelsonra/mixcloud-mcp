import json

from fastmcp import FastMCP

from mixcloud_mcp.api.client import mixcloud_get
from mixcloud_mcp.tools.search.types import SearchResponse


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_user_cloudcasts(username: str, limit: int = 20) -> str:
        """Get a list of mixes uploaded by a Mixcloud user.

        Args:
            username: The Mixcloud username, e.g. "NTSRadio"
            limit: Number of results to return (default 20, max 100)
        """
        clean = username.strip().strip("/").strip()
        raw = await mixcloud_get(f"/{clean}/cloudcasts/", params={"limit": limit})
        results = SearchResponse.model_validate(raw)
        return json.dumps([item.model_dump() for item in results.data], indent=2)
