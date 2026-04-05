"""Entry point for stdio transport — used with Claude Desktop."""
from dotenv import load_dotenv

load_dotenv()

from mixcloud_mcp.server import mcp  # noqa: E402


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
