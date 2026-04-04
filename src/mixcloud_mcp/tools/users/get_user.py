import json
from fastmcp import FastMCP
from mixcloud_mcp.api.client import mixcloud_get
from .types import User


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_user(username: str) -> str:
        """Get a Mixcloud user's profile by username.

        Args:
            username: The Mixcloud username, e.g. "NTSRadio"
        """
        clean = username.strip().strip("/").strip()
        raw = await mixcloud_get(f"/{clean}/")
        result = User.model_validate(raw)
        return json.dumps(result.model_dump(), indent=2)
