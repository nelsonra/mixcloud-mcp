from fastmcp import FastMCP

from .get_cloudcast import register as register_get_cloudcast


def register(mcp: FastMCP) -> None:
    register_get_cloudcast(mcp)
