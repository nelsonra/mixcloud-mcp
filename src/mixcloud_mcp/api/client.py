import json
import os
import sys
import httpx

BASE_URL = "https://api.mixcloud.com"
UPLOAD_URL = "https://upload.mixcloud.com"


def _params(extra: dict | None = None) -> dict:
    """Inject access token into query params if set in env."""
    token = os.getenv("MIXCLOUD_ACCESS_TOKEN")
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
) -> dict:
    """POST multipart/form-data to the Mixcloud upload endpoint.

    Mixcloud's upload API lives on a separate host (upload.mixcloud.com).
    httpx expects file fields as (filename, bytes, content_type) tuples in the
    `files` kwarg, and scalar fields in the `data` kwarg — it handles the
    multipart boundary automatically. Never set Content-Type manually when using
    `files`; httpx would override it and remove the boundary parameter.

    Raises:
        RuntimeError: If MIXCLOUD_ACCESS_TOKEN is not set.
        httpx.HTTPStatusError: If Mixcloud returns a 4xx or 5xx response.
    """
    token = os.getenv("MIXCLOUD_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("MIXCLOUD_ACCESS_TOKEN is not set")

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
