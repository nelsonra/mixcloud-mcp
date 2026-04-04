import os
from dotenv import load_dotenv

load_dotenv()

from .server import mcp  # noqa: E402

if __name__ == "__main__":
    port = int(os.getenv("MCP_PORT", "8000"))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
