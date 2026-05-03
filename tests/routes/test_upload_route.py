import pytest
import httpx
from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette

from mixcloud_mcp.routes.upload import route


@pytest.fixture
def app():
    return Starlette(routes=[route])


@pytest.fixture
def client(app):
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_missing_mp3_returns_400(client):
    response = await client.post("/upload", data={"name": "My Mix"})
    assert response.status_code == 400
    assert "mp3" in response.json()["error"]


@pytest.mark.asyncio
async def test_missing_name_returns_400(client):
    response = await client.post(
        "/upload",
        files={"mp3": ("test.mp3", b"fake-audio", "audio/mpeg")},
    )
    assert response.status_code == 400
    assert "name" in response.json()["error"]


@pytest.mark.asyncio
async def test_no_token_returns_500(client):
    with patch(
        "mixcloud_mcp.routes.upload.mixcloud_post_multipart",
        AsyncMock(side_effect=RuntimeError("No Mixcloud access token — set MIXCLOUD_ACCESS_TOKEN or authenticate via OAuth")),
    ):
        response = await client.post(
            "/upload",
            files={"mp3": ("test.mp3", b"fake-audio", "audio/mpeg")},
            data={"name": "My Mix"},
        )
    assert response.status_code == 500
    assert "access token" in response.json()["error"].lower()


@pytest.mark.asyncio
async def test_successful_upload_returns_200(client):
    fake_result = {"result": "https://www.mixcloud.com/djnelson/my-mix/", "url": "https://www.mixcloud.com/djnelson/my-mix/"}
    with patch(
        "mixcloud_mcp.routes.upload.mixcloud_post_multipart",
        AsyncMock(return_value=fake_result),
    ):
        response = await client.post(
            "/upload",
            files={"mp3": ("show.mp3", b"fake-audio", "audio/mpeg")},
            data={"name": "My Mix"},
            headers={"Authorization": "Bearer mixcloud-token-xyz"},
        )
    assert response.status_code == 200
    assert response.json()["result"] == "https://www.mixcloud.com/djnelson/my-mix/"


@pytest.mark.asyncio
async def test_mixcloud_api_error_returns_502(client):
    import httpx as _httpx

    error_response = _httpx.Response(400, text='{"error": {"message": "Restricted content"}}')
    http_error = _httpx.HTTPStatusError("400", request=_httpx.Request("POST", "http://x"), response=error_response)

    with patch(
        "mixcloud_mcp.routes.upload.mixcloud_post_multipart",
        AsyncMock(side_effect=http_error),
    ):
        response = await client.post(
            "/upload",
            files={"mp3": ("show.mp3", b"fake-audio", "audio/mpeg")},
            data={"name": "My Mix"},
            headers={"Authorization": "Bearer mixcloud-token-xyz"},
        )
    assert response.status_code == 502


@pytest.mark.asyncio
async def test_bearer_token_forwarded_to_api(client):
    """The Authorization header's Bearer token is passed to mixcloud_post_multipart."""
    mock_post = AsyncMock(return_value={"result": "ok"})
    with patch("mixcloud_mcp.routes.upload.mixcloud_post_multipart", mock_post):
        await client.post(
            "/upload",
            files={"mp3": ("show.mp3", b"fake-audio", "audio/mpeg")},
            data={"name": "My Mix"},
            headers={"Authorization": "Bearer forwarded-token"},
        )
    assert mock_post.call_args.kwargs["access_token"] == "forwarded-token"


@pytest.mark.asyncio
async def test_upload_records_to_log(client):
    from mixcloud_mcp import upload_log
    upload_log._log.clear()

    with patch(
        "mixcloud_mcp.routes.upload.mixcloud_post_multipart",
        AsyncMock(return_value={"result": "https://www.mixcloud.com/djnelson/my-mix/", "url": "https://www.mixcloud.com/djnelson/my-mix/"}),
    ):
        await client.post(
            "/upload",
            files={"mp3": ("friday.mp3", b"fake-audio", "audio/mpeg")},
            data={"name": "Friday Night Set"},
            headers={"Authorization": "Bearer token"},
        )

    recent = upload_log.recent(1)
    assert len(recent) == 1
    assert recent[0]["name"] == "Friday Night Set"
    assert recent[0]["status"] == "success"
    upload_log._log.clear()
