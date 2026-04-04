from fastmcp import FastMCP
from mixcloud_mcp.tools.search import register as register_search
from mixcloud_mcp.tools.tracks import register as register_tracks
from mixcloud_mcp.tools.users import register as register_users

mcp = FastMCP("Mixcloud MCP Server")

register_search(mcp)
register_tracks(mcp)
register_users(mcp)
