from fastmcp import FastMCP

from mixcloud_mcp.tools.tracks.upload_cloudcast import register as register_upload_cloudcast


def register(mcp: FastMCP) -> None:
    register_upload_cloudcast(mcp)
