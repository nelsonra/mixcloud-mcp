"""Entry point for HTTP (Streamable HTTP) transport — used for hosted/remote clients."""
import os
from dotenv import load_dotenv

load_dotenv()

from mixcloud_mcp.server import mcp  # noqa: E402


def run() -> None:
    port = int(os.getenv("MCP_PORT", "8000"))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    run()
