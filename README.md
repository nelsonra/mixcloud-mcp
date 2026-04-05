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

### Prerequisites
- Python 3.14+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Install

```bash
git clone https://github.com/YOUR_USERNAME/mixcloud-mcp.git
cd mixcloud-mcp
uv sync
cp .env.example .env
```

Edit `.env` and add your credentials (see [Environment variables](#environment-variables)).

### Run locally (stdio — Claude Desktop)

```bash
uv run mixcloud-mcp
```

### Run as HTTP server (hosted / remote clients)

```bash
uv run mixcloud-mcp-http
```

### Test interactively

```bash
uv run fastmcp dev inspector src/mixcloud_mcp/server.py:mcp
```

### Generate an API key (required for HTTP transport)

```bash
uv run mixcloud-mcp-keygen
```

---

## Claude Desktop setup

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mixcloud": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/mixcloud-mcp",
        "python",
        "-m",
        "mixcloud_mcp.stdio"
      ]
    }
  }
}
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `MIXCLOUD_ACCESS_TOKEN` | No | OAuth token — public data works without it, but token increases rate limits |
| `MCP_API_KEY` | HTTP only | Bearer token to protect the HTTP endpoint |
| `MCP_PORT` | No | HTTP server port (default: `8000`) |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

[GNU General Public License v3.0](LICENSE)
