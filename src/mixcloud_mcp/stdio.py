"""Entry point for stdio transport — used with Claude Desktop."""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from mixcloud_mcp.server import mcp  # noqa: E402


def run() -> None:
    client_id = os.getenv("MIXCLOUD_CLIENT_ID")
    client_secret = os.getenv("MIXCLOUD_CLIENT_SECRET")

    if client_id and client_secret:
        from mixcloud_mcp import sidecar
        port = sidecar.start()

        has_token = bool(os.getenv("MIXCLOUD_ACCESS_TOKEN"))
        print(f"[mixcloud-mcp] Sidecar started on http://localhost:{port}", file=sys.stderr)
        print(f"[mixcloud-mcp] Upload endpoint: POST http://localhost:{port}/upload", file=sys.stderr)
        if not has_token:
            print(
                f"[mixcloud-mcp] No Mixcloud token — visit http://localhost:{port}/oauth/authorize to connect your account.",
                file=sys.stderr,
            )

    mcp.run()


if __name__ == "__main__":
    run()
