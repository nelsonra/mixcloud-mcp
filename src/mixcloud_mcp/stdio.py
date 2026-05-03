"""Entry point for stdio transport — used with Claude Desktop."""
import os
import socket
import sys
import time
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

from mixcloud_mcp.server import mcp


def _wait_for_port(port: int, timeout: float = 5.0) -> None:
    """Block until the given localhost port is accepting connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.1)


def run() -> None:
    load_dotenv(Path.home() / ".config" / "mixcloud-mcp" / ".env")
    load_dotenv()  # local .env for dev overrides; won't clobber already-set vars
    client_id = os.getenv("MIXCLOUD_CLIENT_ID")
    client_secret = os.getenv("MIXCLOUD_CLIENT_SECRET")

    if client_id and client_secret:
        from mixcloud_mcp import sidecar
        port = sidecar.start()

        has_token = bool(os.getenv("MIXCLOUD_ACCESS_TOKEN"))
        print(f"[mixcloud-mcp] Sidecar started on http://localhost:{port}", file=sys.stderr)
        print(f"[mixcloud-mcp] Upload: POST http://localhost:{port}/upload", file=sys.stderr)
        if not has_token:
            auth_url = f"http://localhost:{port}/oauth/authorize"
            print(f"[mixcloud-mcp] No token — opening {auth_url}", file=sys.stderr)
            _wait_for_port(port)
            webbrowser.open(auth_url)

    mcp.run()


if __name__ == "__main__":
    run()
