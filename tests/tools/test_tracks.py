import json
import pytest
from unittest.mock import AsyncMock, patch

# Fake Mixcloud API response for a single PowerFM cloudcast
FAKE_CLOUDCAST_RESPONSE = {
    "key": "/PowerFM/powerfm-drivetime-show-2024/",
    "name": "PowerFM Drivetime Show 2024",
    "url": "https://www.mixcloud.com/PowerFM/powerfm-drivetime-show-2024/",
    "slug": "powerfm-drivetime-show-2024",
    "description": "The best in dance and house music on Power FM.",
    "created_time": "2024-03-15T18:00:00Z",
    "updated_time": "2024-03-15T18:05:00Z",
    "audio_length": 3600,
    "play_count": 12450,
    "listener_count": 9800,
    "favorite_count": 340,
    "comment_count": 27,
    "repost_count": 15,
    "tags": [
        {"key": "/tag/house/", "name": "House", "url": "https://www.mixcloud.com/tag/house/"},
        {"key": "/tag/dance/", "name": "Dance", "url": "https://www.mixcloud.com/tag/dance/"},
    ],
    "user": {
        "key": "/PowerFM/",
        "name": "Power FM",
        "username": "PowerFM",
        "url": "https://www.mixcloud.com/PowerFM/",
    },
}


@pytest.mark.asyncio
async def test_get_cloudcast_returns_details():
    """get_cloudcast returns full mix details for a given key."""
    with patch(
        "mixcloud_mcp.tools.tracks.get_cloudcast.mixcloud_get",
        AsyncMock(return_value=FAKE_CLOUDCAST_RESPONSE),
    ):
        from mixcloud_mcp.tools.tracks.get_cloudcast import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_cloudcast")
        result = await tool.fn(cloudcast_key="/PowerFM/powerfm-drivetime-show-2024/")

        data = json.loads(result)
        assert data["key"] == "/PowerFM/powerfm-drivetime-show-2024/"
        assert data["name"] == "PowerFM Drivetime Show 2024"
        assert data["user"]["username"] == "PowerFM"


@pytest.mark.asyncio
async def test_get_cloudcast_prepends_slash():
    """get_cloudcast prepends a leading slash if the key is missing one."""
    mock_get = AsyncMock(return_value=FAKE_CLOUDCAST_RESPONSE)
    with patch("mixcloud_mcp.tools.tracks.get_cloudcast.mixcloud_get", mock_get):
        from mixcloud_mcp.tools.tracks.get_cloudcast import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_cloudcast")
        await tool.fn(cloudcast_key="PowerFM/powerfm-drivetime-show-2024/")

        path_called = mock_get.call_args.args[0]
        assert path_called.startswith("/")


@pytest.mark.asyncio
async def test_get_cloudcast_strips_whitespace():
    """Whitespace in cloudcast_key is stripped before the API call."""
    mock_get = AsyncMock(return_value=FAKE_CLOUDCAST_RESPONSE)
    with patch("mixcloud_mcp.tools.tracks.get_cloudcast.mixcloud_get", mock_get):
        from mixcloud_mcp.tools.tracks.get_cloudcast import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_cloudcast")
        await tool.fn(cloudcast_key="  /PowerFM/powerfm-drivetime-show-2024/  ")

        path_called = mock_get.call_args.args[0]
        assert " " not in path_called


@pytest.mark.asyncio
async def test_get_cloudcast_fields():
    """Returned dict contains all expected fields including engagement counts."""
    with patch(
        "mixcloud_mcp.tools.tracks.get_cloudcast.mixcloud_get",
        AsyncMock(return_value=FAKE_CLOUDCAST_RESPONSE),
    ):
        from mixcloud_mcp.tools.tracks.get_cloudcast import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_cloudcast")
        result = await tool.fn(cloudcast_key="/PowerFM/powerfm-drivetime-show-2024/")

        data = json.loads(result)
        for field in ("key", "name", "url", "slug", "description", "audio_length",
                      "play_count", "listener_count", "favorite_count", "comment_count",
                      "repost_count", "tags", "user"):
            assert field in data, f"Missing field: {field}"
