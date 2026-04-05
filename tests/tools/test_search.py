import json
import pytest
from unittest.mock import AsyncMock, patch

# Fake Mixcloud API response for a PowerFM search
FAKE_SEARCH_RESPONSE = {
    "data": [
        {
            "key": "/PowerFM/powerfm-drivetime-show-2024/",
            "name": "PowerFM Drivetime Show 2024",
            "url": "https://www.mixcloud.com/PowerFM/powerfm-drivetime-show-2024/",
            "slug": "powerfm-drivetime-show-2024",
            "created_time": "2024-03-15T18:00:00Z",
            "audio_length": 3600,
            "play_count": 12450,
            "listener_count": 9800,
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
        },
        {
            "key": "/PowerFM/weekend-warmup-mix/",
            "name": "Weekend Warmup Mix",
            "url": "https://www.mixcloud.com/PowerFM/weekend-warmup-mix/",
            "slug": "weekend-warmup-mix",
            "created_time": "2024-04-01T20:00:00Z",
            "audio_length": 5400,
            "play_count": 8200,
            "listener_count": 6100,
            "tags": [
                {"key": "/tag/dance/", "name": "Dance", "url": "https://www.mixcloud.com/tag/dance/"},
            ],
            "user": {
                "key": "/PowerFM/",
                "name": "Power FM",
                "username": "PowerFM",
                "url": "https://www.mixcloud.com/PowerFM/",
            },
        },
    ]
}


@pytest.mark.asyncio
async def test_search_returns_results():
    """search_cloudcasts returns a list of cloudcast results."""
    with patch(
        "mixcloud_mcp.tools.search.search_cloudcasts.mixcloud_get",
        AsyncMock(return_value=FAKE_SEARCH_RESPONSE),
    ):
        from mixcloud_mcp.tools.search.search_cloudcasts import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("search_cloudcasts")
        result = await tool.fn(query="PowerFM", limit=20)

        data = json.loads(result)
        assert len(data) == 2
        assert data[0]["key"] == "/PowerFM/powerfm-drivetime-show-2024/"
        assert data[0]["user"]["username"] == "PowerFM"


@pytest.mark.asyncio
async def test_search_strips_query_whitespace():
    """Leading/trailing whitespace in query is stripped before the API call."""
    mock_get = AsyncMock(return_value=FAKE_SEARCH_RESPONSE)
    with patch("mixcloud_mcp.tools.search.search_cloudcasts.mixcloud_get", mock_get):
        from mixcloud_mcp.tools.search.search_cloudcasts import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("search_cloudcasts")
        await tool.fn(query="  PowerFM  ", limit=5)

        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["params"]["q"] == "PowerFM"
        assert call_kwargs.kwargs["params"]["limit"] == 5


@pytest.mark.asyncio
async def test_search_empty_results():
    """search_cloudcasts handles an empty result set gracefully."""
    with patch(
        "mixcloud_mcp.tools.search.search_cloudcasts.mixcloud_get",
        AsyncMock(return_value={"data": []}),
    ):
        from mixcloud_mcp.tools.search.search_cloudcasts import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("search_cloudcasts")
        result = await tool.fn(query="xyzzy_nothing_matches", limit=20)

        assert json.loads(result) == []


@pytest.mark.asyncio
async def test_search_result_fields():
    """Each result contains the expected fields."""
    with patch(
        "mixcloud_mcp.tools.search.search_cloudcasts.mixcloud_get",
        AsyncMock(return_value=FAKE_SEARCH_RESPONSE),
    ):
        from mixcloud_mcp.tools.search.search_cloudcasts import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("search_cloudcasts")
        result = await tool.fn(query="PowerFM", limit=20)

        item = json.loads(result)[0]
        for field in ("key", "name", "url", "slug", "created_time", "audio_length", "play_count", "listener_count", "tags", "user"):
            assert field in item, f"Missing field: {field}"
