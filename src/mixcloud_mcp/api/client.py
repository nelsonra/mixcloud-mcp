import os
import httpx

BASE_URL = "https://api.mixcloud.com"


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
        return response.json()
