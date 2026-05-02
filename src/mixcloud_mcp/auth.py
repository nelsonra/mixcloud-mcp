"""Mixcloud-specific OAuth proxy and token verifier for the HTTP transport."""
import json
from urllib.parse import parse_qsl

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastmcp.server.auth import TokenVerifier
from fastmcp.server.auth.oauth_proxy.proxy import OAuthProxy
from mcp.server.auth.provider import AccessToken

MIXCLOUD_AUTH_URL = "https://www.mixcloud.com/oauth/authorize"
MIXCLOUD_TOKEN_URL = "https://www.mixcloud.com/oauth/access_token"


def _mixcloud_token_compliance_hook(response: httpx.Response) -> httpx.Response:
    """Convert Mixcloud's URL-encoded token response to JSON.

    Mixcloud returns access_token=xxx as plain text / URL-encoded form instead
    of the standard application/json body that authlib expects. This hook
    intercepts the raw response and re-wraps it so authlib can parse it.
    """
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        return response
    data = dict(parse_qsl(response.text))
    return httpx.Response(
        status_code=response.status_code,
        headers={"content-type": "application/json"},
        content=json.dumps(data).encode(),
    )


class MixcloudOAuthProxy(OAuthProxy):
    """OAuthProxy subclass that handles Mixcloud's non-standard OAuth behaviour.

    Two Mixcloud quirks:
    - Token endpoint uses GET query params instead of POST body.
      Handled by passing extra_token_params={"method": "GET"} at construction,
      which is spread into authlib's fetch_token(**...) call.
    - Token response is URL-encoded text (access_token=xxx) instead of JSON.
      Handled by a compliance hook registered on the AsyncOAuth2Client.
    """

    def _create_upstream_oauth_client(self) -> AsyncOAuth2Client:
        client = super()._create_upstream_oauth_client()
        client.register_compliance_hook(
            "access_token_response", _mixcloud_token_compliance_hook
        )
        return client


class MixcloudTokenVerifier(TokenVerifier):
    """Validates Mixcloud access tokens by calling the /me endpoint.

    Returns an AccessToken whose .token field is the raw Mixcloud access token,
    so tools can retrieve it via get_access_token().token and forward it to the
    upload endpoint.
    """

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token:
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.mixcloud.com/me",
                    params={"access_token": token},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return AccessToken(
                        token=token,
                        client_id=data.get("key", "/unknown/").strip("/"),
                        scopes=[],
                    )
        except Exception:
            pass
        return None
