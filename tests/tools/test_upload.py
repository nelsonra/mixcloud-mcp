import json
import os
import pytest
from unittest.mock import patch, MagicMock

from fastmcp import FastMCP


def _make_mcp():
    return FastMCP("test")


# --- _upload_url() ---

def test_upload_url_defaults_to_port_8000(monkeypatch):
    monkeypatch.delenv("MCP_PUBLIC_URL", raising=False)
    monkeypatch.delenv("UPLOAD_PORT", raising=False)
    monkeypatch.delenv("MCP_PORT", raising=False)

    from mixcloud_mcp.tools.tracks.upload_cloudcast import _upload_url
    assert _upload_url() == "http://localhost:8000/upload"


def test_upload_url_uses_upload_port(monkeypatch):
    monkeypatch.delenv("MCP_PUBLIC_URL", raising=False)
    monkeypatch.setenv("UPLOAD_PORT", "4321")
    monkeypatch.delenv("MCP_PORT", raising=False)

    from mixcloud_mcp.tools.tracks.upload_cloudcast import _upload_url
    assert _upload_url() == "http://localhost:4321/upload"


def test_upload_url_prefers_mcp_public_url(monkeypatch):
    monkeypatch.setenv("MCP_PUBLIC_URL", "https://my-server.example.com")

    from mixcloud_mcp.tools.tracks.upload_cloudcast import _upload_url
    assert _upload_url() == "https://my-server.example.com/upload"


def test_upload_url_strips_trailing_slash_from_public_url(monkeypatch):
    monkeypatch.setenv("MCP_PUBLIC_URL", "https://my-server.example.com/")

    from mixcloud_mcp.tools.tracks.upload_cloudcast import _upload_url
    assert _upload_url() == "https://my-server.example.com/upload"


# --- upload_cloudcast tool ---

@pytest.mark.asyncio
async def test_upload_cloudcast_uses_oauth_token():
    """When get_access_token() returns a token, it takes priority over env var."""
    mock_access = MagicMock()
    mock_access.token = "oauth-token-xyz"

    with patch("mixcloud_mcp.tools.tracks.upload_cloudcast.get_access_token", return_value=mock_access):
        with patch("mixcloud_mcp.tools.tracks.upload_cloudcast._upload_url", return_value="http://localhost:8000/upload"):
            mcp = _make_mcp()
            from mixcloud_mcp.tools.tracks.upload_cloudcast import register
            register(mcp)
            tool = await mcp.get_tool("upload_cloudcast")
            result = json.loads(await tool.fn())

    assert result["upload_token"] == "oauth-token-xyz"


@pytest.mark.asyncio
async def test_upload_cloudcast_falls_back_to_env_token(monkeypatch):
    """Falls back to MIXCLOUD_ACCESS_TOKEN when no OAuth session token exists."""
    monkeypatch.setenv("MIXCLOUD_ACCESS_TOKEN", "env-token-abc")

    with patch("mixcloud_mcp.tools.tracks.upload_cloudcast.get_access_token", return_value=None):
        with patch("mixcloud_mcp.tools.tracks.upload_cloudcast._upload_url", return_value="http://localhost:8000/upload"):
            mcp = _make_mcp()
            from mixcloud_mcp.tools.tracks.upload_cloudcast import register
            register(mcp)
            tool = await mcp.get_tool("upload_cloudcast")
            result = json.loads(await tool.fn())

    assert result["upload_token"] == "env-token-abc"


@pytest.mark.asyncio
async def test_upload_cloudcast_token_is_none_when_unauthenticated(monkeypatch):
    monkeypatch.delenv("MIXCLOUD_ACCESS_TOKEN", raising=False)

    with patch("mixcloud_mcp.tools.tracks.upload_cloudcast.get_access_token", return_value=None):
        with patch("mixcloud_mcp.tools.tracks.upload_cloudcast._upload_url", return_value="http://localhost:8000/upload"):
            mcp = _make_mcp()
            from mixcloud_mcp.tools.tracks.upload_cloudcast import register
            register(mcp)
            tool = await mcp.get_tool("upload_cloudcast")
            result = json.loads(await tool.fn())

    assert result["upload_token"] is None


@pytest.mark.asyncio
async def test_upload_cloudcast_passes_name_param():
    with patch("mixcloud_mcp.tools.tracks.upload_cloudcast.get_access_token", return_value=None):
        with patch("mixcloud_mcp.tools.tracks.upload_cloudcast._upload_url", return_value="http://localhost:8000/upload"):
            mcp = _make_mcp()
            from mixcloud_mcp.tools.tracks.upload_cloudcast import register
            register(mcp)
            tool = await mcp.get_tool("upload_cloudcast")
            result = json.loads(await tool.fn(name="Friday Night Mix"))

    assert result["name"] == "Friday Night Mix"


@pytest.mark.asyncio
async def test_upload_cloudcast_includes_upload_url():
    with patch("mixcloud_mcp.tools.tracks.upload_cloudcast.get_access_token", return_value=None):
        with patch("mixcloud_mcp.tools.tracks.upload_cloudcast._upload_url", return_value="http://localhost:4321/upload"):
            mcp = _make_mcp()
            from mixcloud_mcp.tools.tracks.upload_cloudcast import register
            register(mcp)
            tool = await mcp.get_tool("upload_cloudcast")
            result = json.loads(await tool.fn())

    assert result["upload_url"] == "http://localhost:4321/upload"
