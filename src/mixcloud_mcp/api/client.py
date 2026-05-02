import json
import os
import sys
import httpx

BASE_URL = "https://api.mixcloud.com"
UPLOAD_URL = "https://upload.mixcloud.com"


def _token() -> str | None:
    """Return the best available Mixcloud access token for the current context.

    In HTTP OAuth mode, get_access_token() returns the token stored by
    MixcloudOAuthProxy for this session — authenticated requests get higher
    Mixcloud rate limits. Falls back to MIXCLOUD_ACCESS_TOKEN env var (set by
    the sidecar OAuth callback or manually via mixcloud-mcp-oauth).
    """
    try:
        from fastmcp.server.dependencies import get_access_token
        token_obj = get_access_token()
        if token_obj and token_obj.token:
            return token_obj.token
    except Exception:
        pass
    return os.getenv("MIXCLOUD_ACCESS_TOKEN") or None


def _params(extra: dict | None = None) -> dict:
    token = _token()
    base = {"access_token": token} if token else {}
    return {**base, **(extra or {})}


async def mixcloud_get(path: str, params: dict | None = None) -> dict:
    """GET a Mixcloud API endpoint. Returns parsed JSON.

    Args:
        path: API path, e.g. "/search/" or "/someuser/cloudcasts/"
        params: Optional query parameters, e.g. {"q": "deep house", "type": "cloudcast"}

    Raises:
        httpx.HTTPStatusError: if Mixcloud returns a 4xx or 5xx response
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}{path}",
            params=_params(params),
        )
        response.raise_for_status()
        return response.json() if response.content else {}


async def mixcloud_post_multipart(
    mp3_bytes: bytes,
    filename: str,
    data: dict,
    picture_bytes: bytes | None = None,
    picture_filename: str | None = None,
    access_token: str | None = None,
) -> dict:
    """POST multipart/form-data to the Mixcloud upload endpoint.

    Mixcloud's upload API lives on a separate host (upload.mixcloud.com).
    httpx expects file fields as (filename, bytes, content_type) tuples in the
    `files` kwarg, and scalar fields in the `data` kwarg — it handles the
    multipart boundary automatically. Never set Content-Type manually when using
    `files`; httpx would override it and remove the boundary parameter.

    Args:
        access_token: Mixcloud access token. If None, falls back to
            MIXCLOUD_ACCESS_TOKEN env var (used in non-OAuth deployments).

    Raises:
        RuntimeError: If no access token is available.
        httpx.HTTPStatusError: If Mixcloud returns a 4xx or 5xx response.
    """
    token = access_token or os.getenv("MIXCLOUD_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("No Mixcloud access token — set MIXCLOUD_ACCESS_TOKEN or authenticate via OAuth")

    files: dict = {"mp3": (filename, mp3_bytes, "audio/mpeg")}
    if picture_bytes and picture_filename:
        files["picture"] = (picture_filename, picture_bytes, "image/jpeg")

    # Large files can take minutes — use a generous timeout.
    async with httpx.AsyncClient(timeout=600.0) as client:
        response = await client.post(
            "https://upload.mixcloud.com/upload/",
            data={**data, "access_token": token},
            files=files,
        )	
        try:
            body = json.dumps(response.json(), indent=2)
        except Exception:
            body = response.text or "(empty)"
        print(f"[mixcloud upload] {response.status_code}\n{body}", file=sys.stderr)
        response.raise_for_status()
        return response.json() if response.content else {}
