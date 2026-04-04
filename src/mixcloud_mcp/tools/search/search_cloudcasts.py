import json
from fastmcp import FastMCP
from ...api.client import mixcloud_get
from .types import SearchResponse


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def search_cloudcasts(query: str, limit: int = 20) -> str:
        """Search Mixcloud for mixes (cloudcasts) by keyword.

        Args:
            query: Search term, e.g. "deep house" or "NTS Radio"
            limit: Number of results to return (default 20, max 100)
        """
        raw = await mixcloud_get("/search/", params={"q": query.strip(), "type": "cloudcast", "limit": limit})
        results = SearchResponse.model_validate(raw)
        return json.dumps([item.model_dump() for item in results.data], indent=2)
