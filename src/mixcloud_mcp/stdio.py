from dotenv import load_dotenv

load_dotenv()

from .server import mcp  # noqa: E402

if __name__ == "__main__":
    mcp.run()
