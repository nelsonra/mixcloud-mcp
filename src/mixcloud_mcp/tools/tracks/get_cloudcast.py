import json
from fastmcp import FastMCP
from mixcloud_mcp.api.client import mixcloud_get
from .types import Cloudcast


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_cloudcast(cloudcast_key: str) -> str:
        """Get details of a specific Mixcloud mix by its key.

        Args:
            cloudcast_key: The mix key, e.g. "/NTSRadio/nts-breakfast-show/"
        """
        key = "".join(cloudcast_key.split())
        if not key.startswith("/"):
            key = f"/{key}"
        raw = await mixcloud_get(key)
        result = Cloudcast.model_validate(raw)
        return json.dumps(result.model_dump(), indent=2)
