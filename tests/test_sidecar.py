import os
from pathlib import Path
from unittest.mock import patch

import pytest


def test_user_config_file_path_structure():
    """Token file is always under ~/.config/mixcloud-mcp/.env."""
    from mixcloud_mcp.sidecar import _user_config_file
    result = _user_config_file()
    assert result.name == ".env"
    assert result.parent.name == "mixcloud-mcp"
    assert result.parent.parent.name == ".config"


def test_user_config_file_creates_directory(tmp_path):
    config_dir = tmp_path / ".config" / "mixcloud-mcp"
    assert not config_dir.exists()

    with patch("mixcloud_mcp.sidecar.Path") as MockPath:
        MockPath.home.return_value = tmp_path
        # Delegate everything except home() to the real Path
        MockPath.side_effect = lambda *a, **kw: Path(*a, **kw)
        from mixcloud_mcp.sidecar import _user_config_file
        _user_config_file()

    assert config_dir.is_dir()


def test_persist_token_sets_env_var(tmp_path):
    env_file = tmp_path / ".env"
    saved = os.environ.get("MIXCLOUD_ACCESS_TOKEN")
    try:
        with patch("mixcloud_mcp.sidecar._user_config_file", return_value=env_file):
            from mixcloud_mcp.sidecar import _persist_token
            _persist_token("test-sidecar-token")
            assert os.environ.get("MIXCLOUD_ACCESS_TOKEN") == "test-sidecar-token"
    finally:
        if saved is None:
            os.environ.pop("MIXCLOUD_ACCESS_TOKEN", None)
        else:
            os.environ["MIXCLOUD_ACCESS_TOKEN"] = saved


def test_persist_token_writes_to_config_file(tmp_path):
    env_file = tmp_path / ".env"
    with patch("mixcloud_mcp.sidecar._user_config_file", return_value=env_file):
        from mixcloud_mcp.sidecar import _persist_token
        _persist_token("written-token")

    content = env_file.read_text()
    assert "written-token" in content
    os.environ.pop("MIXCLOUD_ACCESS_TOKEN", None)
