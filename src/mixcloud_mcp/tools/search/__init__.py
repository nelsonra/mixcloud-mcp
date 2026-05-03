from fastmcp import FastMCP

from .search_cloudcasts import register as register_search_cloudcasts


def register(mcp: FastMCP) -> None:
    register_search_cloudcasts(mcp)
