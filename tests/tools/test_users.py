import json
import pytest
from unittest.mock import AsyncMock, patch

# Fake Mixcloud API response for djnelson's profile
FAKE_USER_RESPONSE = {
    "key": "/djnelson/",
    "name": "DJ Nelson",
    "username": "djnelson",
    "url": "https://www.mixcloud.com/djnelson/",
    "biog": "DJ and radio presenter. Catch me on Power FM.",
    "created_time": "2012-06-01T10:00:00Z",
    "follower_count": 4800,
    "following_count": 320,
    "cloudcast_count": 210,
    "city": "Johannesburg",
    "country": "South Africa",
    "is_pro": False,
    "is_premium": False,
}

# Fake cloudcasts list for djnelson
FAKE_CLOUDCASTS_RESPONSE = {
    "data": [
        {
            "key": "/djnelson/power-fm-saturday-night/",
            "name": "Power FM Saturday Night",
            "url": "https://www.mixcloud.com/djnelson/power-fm-saturday-night/",
            "slug": "power-fm-saturday-night",
            "created_time": "2024-02-10T22:00:00Z",
            "audio_length": 7200,
            "play_count": 5300,
            "listener_count": 4100,
            "tags": [
                {"key": "/tag/house/", "name": "House", "url": "https://www.mixcloud.com/tag/house/"},
            ],
            "user": {
                "key": "/djnelson/",
                "name": "DJ Nelson",
                "username": "djnelson",
                "url": "https://www.mixcloud.com/djnelson/",
            },
        },
    ]
}

# Fake followers list for djnelson
FAKE_FOLLOWERS_RESPONSE = {
    "data": [
        {
            "key": "/PowerFM/",
            "name": "Power FM",
            "username": "PowerFM",
            "url": "https://www.mixcloud.com/PowerFM/",
        },
        {
            "key": "/house-heads/",
            "name": "House Heads SA",
            "username": "house-heads",
            "url": "https://www.mixcloud.com/house-heads/",
        },
    ]
}

# Fake following list for djnelson
FAKE_FOLLOWING_RESPONSE = {
    "data": [
        {
            "key": "/PowerFM/",
            "name": "Power FM",
            "username": "PowerFM",
            "url": "https://www.mixcloud.com/PowerFM/",
        },
    ]
}


# --- get_user ---

@pytest.mark.asyncio
async def test_get_user_returns_profile():
    """get_user returns the full profile for djnelson."""
    with patch(
        "mixcloud_mcp.tools.users.get_user.mixcloud_get",
        AsyncMock(return_value=FAKE_USER_RESPONSE),
    ):
        from mixcloud_mcp.tools.users.get_user import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_user")
        result = await tool.fn(username="djnelson")

        data = json.loads(result)
        assert data["username"] == "djnelson"
        assert data["follower_count"] == 4800
        assert data["city"] == "Johannesburg"


@pytest.mark.asyncio
async def test_get_user_strips_slashes():
    """get_user strips leading/trailing slashes from the username."""
    mock_get = AsyncMock(return_value=FAKE_USER_RESPONSE)
    with patch("mixcloud_mcp.tools.users.get_user.mixcloud_get", mock_get):
        from mixcloud_mcp.tools.users.get_user import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_user")
        await tool.fn(username="/djnelson/")

        path_called = mock_get.call_args.args[0]
        assert path_called == "/djnelson/"


@pytest.mark.asyncio
async def test_get_user_fields():
    """Returned profile contains all expected fields."""
    with patch(
        "mixcloud_mcp.tools.users.get_user.mixcloud_get",
        AsyncMock(return_value=FAKE_USER_RESPONSE),
    ):
        from mixcloud_mcp.tools.users.get_user import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_user")
        result = await tool.fn(username="djnelson")

        data = json.loads(result)
        for field in ("key", "name", "username", "url", "biog", "created_time",
                      "follower_count", "following_count", "cloudcast_count"):
            assert field in data, f"Missing field: {field}"


# --- get_user_cloudcasts ---

@pytest.mark.asyncio
async def test_get_user_cloudcasts_returns_list():
    """get_user_cloudcasts returns djnelson's mixes."""
    with patch(
        "mixcloud_mcp.tools.users.get_user_cloudcasts.mixcloud_get",
        AsyncMock(return_value=FAKE_CLOUDCASTS_RESPONSE),
    ):
        from mixcloud_mcp.tools.users.get_user_cloudcasts import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_user_cloudcasts")
        result = await tool.fn(username="djnelson", limit=20)

        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["key"] == "/djnelson/power-fm-saturday-night/"


@pytest.mark.asyncio
async def test_get_user_cloudcasts_passes_limit():
    """get_user_cloudcasts forwards the limit param to the API."""
    mock_get = AsyncMock(return_value=FAKE_CLOUDCASTS_RESPONSE)
    with patch("mixcloud_mcp.tools.users.get_user_cloudcasts.mixcloud_get", mock_get):
        from mixcloud_mcp.tools.users.get_user_cloudcasts import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_user_cloudcasts")
        await tool.fn(username="djnelson", limit=5)

        assert mock_get.call_args.kwargs["params"]["limit"] == 5


# --- get_user_followers ---

@pytest.mark.asyncio
async def test_get_user_followers_returns_list():
    """get_user_followers returns djnelson's followers."""
    with patch(
        "mixcloud_mcp.tools.users.get_user_followers.mixcloud_get",
        AsyncMock(return_value=FAKE_FOLLOWERS_RESPONSE),
    ):
        from mixcloud_mcp.tools.users.get_user_followers import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_user_followers")
        result = await tool.fn(username="djnelson", limit=20)

        data = json.loads(result)
        assert len(data) == 2
        assert data[0]["username"] == "PowerFM"


# --- get_user_following ---

@pytest.mark.asyncio
async def test_get_user_following_returns_list():
    """get_user_following returns who djnelson follows."""
    with patch(
        "mixcloud_mcp.tools.users.get_user_following.mixcloud_get",
        AsyncMock(return_value=FAKE_FOLLOWING_RESPONSE),
    ):
        from mixcloud_mcp.tools.users.get_user_following import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_user_following")
        result = await tool.fn(username="djnelson", limit=20)

        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["username"] == "PowerFM"
