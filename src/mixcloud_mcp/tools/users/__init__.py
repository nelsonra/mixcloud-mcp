from fastmcp import FastMCP

from .get_user import register as register_get_user
from .get_user_cloudcasts import register as register_get_user_cloudcasts
from .get_user_followers import register as register_get_user_followers
from .get_user_following import register as register_get_user_following


def register(mcp: FastMCP) -> None:
    register_get_user(mcp)
    register_get_user_cloudcasts(mcp)
    register_get_user_followers(mcp)
    register_get_user_following(mcp)
