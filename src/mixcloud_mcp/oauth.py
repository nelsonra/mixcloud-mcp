"""One-time OAuth flow to obtain a Mixcloud access token and save it to .env."""
import os
import socket
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx
from dotenv import load_dotenv, set_key

AUTHORIZE_URL = "https://www.mixcloud.com/oauth/authorize"
TOKEN_URL = "https://www.mixcloud.com/oauth/access_token"


def _free_port() -> int:
    """Bind to port 0 to let the OS pick a free port, then release it."""
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _find_env_file() -> Path:
    """Walk up from cwd to find an existing .env, or default to cwd/.env."""
    path = Path.cwd()
    while path != path.parent:
        candidate = path / ".env"
        if candidate.exists():
            return candidate
        path = path.parent
    return Path.cwd() / ".env"


def run() -> None:
    load_dotenv()

    client_id = os.getenv("MIXCLOUD_CLIENT_ID")
    client_secret = os.getenv("MIXCLOUD_CLIENT_SECRET")

    if not client_id or not client_secret:
        print(
            "ERROR: MIXCLOUD_CLIENT_ID and MIXCLOUD_CLIENT_SECRET must be set in .env\n"
            "       Get them from https://www.mixcloud.com/developers/",
            file=sys.stderr,
        )
        sys.exit(1)

    port = _free_port()
    redirect_uri = f"http://localhost:{port}/callback"

    # Threading event + shared dict let the HTTP handler signal the main thread.
    done = threading.Event()
    result: dict[str, str | None] = {"code": None, "error": None}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)

            if parsed.path != "/callback":
                self._respond(400, "Not found")
                return

            if "error" in params:
                result["error"] = params["error"][0]
                self._respond(400, f"Authorization denied: {result['error']}")
            else:
                result["code"] = params.get("code", [None])[0]
                self._respond(200, "Authorization successful — you can close this tab.")

            done.set()

        def _respond(self, status: int, message: str) -> None:
            body = f"<html><body><p>{message}</p></body></html>".encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            pass  # suppress per-request noise

    server = HTTPServer(("localhost", port), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    auth_params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
    })
    auth_url = f"{AUTHORIZE_URL}?{auth_params}"

    print("Opening browser for Mixcloud authorization...")
    print(f"If the browser does not open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    print("Waiting for authorization (timeout: 120s)...")
    timed_out = not done.wait(timeout=120)
    server.shutdown()

    if timed_out:
        print("ERROR: Timed out waiting for authorization", file=sys.stderr)
        sys.exit(1)

    if result["error"] or not result["code"]:
        print(f"ERROR: {result['error'] or 'No authorization code received'}", file=sys.stderr)
        sys.exit(1)

    # Mixcloud's token endpoint is a GET, not a POST — uncommon but valid OAuth 2.0.
    response = httpx.get(TOKEN_URL, params={
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "client_secret": client_secret,
        "code": result["code"],
    })
    response.raise_for_status()
    data = response.json()

    if "access_token" not in data:
        print(f"ERROR: Unexpected response from Mixcloud: {data}", file=sys.stderr)
        sys.exit(1)

    token: str = data["access_token"]
    env_file = _find_env_file()

    # set_key updates the key in place without touching other values.
    set_key(str(env_file), "MIXCLOUD_ACCESS_TOKEN", token, quote_mode="never")

    print(f"Access token saved to {env_file}")
    print("Restart the MCP server to pick up the new token.")


if __name__ == "__main__":
    run()
