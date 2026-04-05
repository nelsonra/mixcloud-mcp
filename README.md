# mixcloud-mcp

A [FastMCP](https://github.com/jlowin/fastmcp) server that bridges the [Mixcloud API](https://www.mixcloud.com/developers/) to AI assistants via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/).

Ask Claude to search for mixes, look up artists, browse a user's uploads, and more — all powered by the Mixcloud public API.

---

## Tools

| Tool | Description |
|---|---|
| `search_cloudcasts` | Search Mixcloud for mixes by keyword |
| `get_cloudcast` | Get details of a specific mix by its key |
| `get_user` | Get a user's profile |
| `get_user_cloudcasts` | List a user's uploaded mixes |
| `get_user_followers` | List a user's followers |
| `get_user_following` | List who a user follows |

---

## Quickstart

No install needed. Add the following to your Claude Desktop config and restart — `uvx` fetches the package from PyPI automatically.

See [Claude Desktop setup](#claude-desktop-setup) below.

---

## Claude Desktop setup

Add to your `claude_desktop_config.json`
(location: `~/Library/Application Support/Claude/claude_desktop_config.json` on Mac):

```json
{
  "mcpServers": {
    "mixcloud": {
      "command": "uvx",
      "args": ["mixcloud-mcp"]
    }
  }
}
```

> **Tip:** `uvx` runs the package directly from PyPI without a separate install step — the Python equivalent of `npx`.
> If Claude Desktop can't find `uvx`, use the full path: run `which uvx` in your terminal.

**Optional: Mixcloud API token**

Public data works without a token. If you have a [Mixcloud API key](https://www.mixcloud.com/developers/), pass it via the `env` block to increase rate limits:

```json
{
  "mcpServers": {
    "mixcloud": {
      "command": "uvx",
      "args": ["mixcloud-mcp"],
      "env": {
        "MIXCLOUD_ACCESS_TOKEN": "<your token>"
      }
    }
  }
}
```

Restart Claude Desktop after editing the config.

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `MIXCLOUD_ACCESS_TOKEN` | No | OAuth token — public data works without it, but increases rate limits |
| `MCP_API_KEY` | HTTP only | Bearer token to protect the HTTP endpoint. Generate with `mixcloud-mcp-keygen` |
| `MCP_PORT` | No | HTTP server port (default: `8000`) |
| `DISABLE_AUTH` | No | Set to `true` to skip auth — local dev only, never in production |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

[GNU General Public License v3.0](LICENSE)
