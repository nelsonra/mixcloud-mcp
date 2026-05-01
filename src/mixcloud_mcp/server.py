from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()
from mixcloud_mcp.tools.search import register as register_search
from mixcloud_mcp.tools.tracks import register as register_tracks
from mixcloud_mcp.tools.users import register as register_users
from mixcloud_mcp.tools.upload import register as register_upload

mcp = FastMCP("Mixcloud MCP Server")

register_search(mcp)
register_tracks(mcp)
register_users(mcp)
register_upload(mcp)