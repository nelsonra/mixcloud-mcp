# mixcloud-mcp

A [FastMCP](https://github.com/jlowin/fastmcp) server that bridges the [Mixcloud API](https://www.mixcloud.com/developers/) to AI assistants via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/).

Ask Claude to search for mixes, look up artists, browse uploads, and upload recordings directly to Mixcloud — all from the conversation.

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
| `upload_cloudcast` | Upload a recording to Mixcloud (opens a file picker UI) |

---

## Quickstart — stdio (Claude Desktop, local)

No install needed. Add to your `claude_desktop_config.json` and restart:

**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mixcloud": {
      "command": "/path/to/uvx",
      "args": ["mixcloud-mcp"]
    }
  }
}
```

> **Tip:** Claude Desktop doesn't inherit your shell PATH, so `uvx` must be a full path.
> Run `which uvx` in your terminal to find it — typically `/Users/yourname/.local/bin/uvx`.

Public read-only tools (search, get user, etc.) work immediately without any credentials.

**To enable uploads and authenticated API calls**, add your Mixcloud OAuth app credentials. The server will print an authorize URL to stderr on first start — visit it in your browser once and your token is saved automatically.

```json
{
  "mcpServers": {
    "mixcloud": {
      "command": "/path/to/uvx",
      "args": ["mixcloud-mcp"],
      "env": {
        "MIXCLOUD_CLIENT_ID": "<your client id>",
        "MIXCLOUD_CLIENT_SECRET": "<your client secret>"
      }
    }
  }
}
```

Get your credentials at [mixcloud.com/developers](https://www.mixcloud.com/developers/). Register `http://localhost:4000/oauth/callback` as the redirect URI in your Mixcloud app.

---

## Quickstart — HTTP (hosted server, remote MCP clients)

The HTTP transport is for deploying the server so remote MCP clients can connect to it over the network.

```bash
uvx mixcloud-mcp-http
```

### Authentication

Set `MIXCLOUD_CLIENT_ID` and `MIXCLOUD_CLIENT_SECRET` in your environment to enable OAuth. When a client connects for the first time, they are redirected to Mixcloud to authenticate — no pre-shared token required.

```bash
MIXCLOUD_CLIENT_ID=xxx \
MIXCLOUD_CLIENT_SECRET=xxx \
MCP_PUBLIC_URL=https://your-server.example.com \
uvx mixcloud-mcp-http
```

Register `https://your-server.example.com/auth/callback` as the redirect URI in your Mixcloud app. The `MCP_PUBLIC_URL` must match exactly.

**Without OAuth** you can protect the endpoint with a static bearer token instead:

```bash
MCP_API_KEY=your_secret_key uvx mixcloud-mcp-http
```

Clients connect by adding the server URL to their MCP configuration with `Authorization: Bearer <MCP_API_KEY>`.

---

## Environment variables

### Both transports

| Variable | Default | Description |
|---|---|---|
| `MIXCLOUD_CLIENT_ID` | — | Mixcloud OAuth app client ID. Required for OAuth auth and uploads. |
| `MIXCLOUD_CLIENT_SECRET` | — | Mixcloud OAuth app client secret. Required for OAuth auth and uploads. |
| `MIXCLOUD_ACCESS_TOKEN` | — | Direct Mixcloud token. Alternative to OAuth — set manually or via `mixcloud-mcp-oauth`. |

### stdio only

| Variable | Default | Description |
|---|---|---|
| `UPLOAD_PORT` | `4000` | Port for the sidecar HTTP server (handles uploads and the OAuth callback). |

### HTTP only

| Variable | Default | Description |
|---|---|---|
| `MCP_API_KEY` | — | Bearer token for simple auth (used when OAuth is not configured). Generate with `mixcloud-mcp-keygen`. |
| `MCP_PORT` | `8000` | HTTP server port. |
| `MCP_PUBLIC_URL` | `http://localhost:<MCP_PORT>` | Public base URL of the server. **Must be set for OAuth** — Mixcloud redirects back to `<MCP_PUBLIC_URL>/auth/callback`. |
| `CORS_ORIGIN` | `*` | Allowed CORS origin for the upload endpoint. Lock this down in production. |
| `DISABLE_AUTH` | — | Set to `true` to skip auth — local dev only, never in production. |

---

## How authentication works

### stdio — sidecar OAuth

When `MIXCLOUD_CLIENT_ID` and `MIXCLOUD_CLIENT_SECRET` are set, the server starts a lightweight sidecar HTTP server (on `UPLOAD_PORT`, default 4000) before the MCP process starts. On first run, if no token is present, it prints:

```
[mixcloud-mcp] No Mixcloud token — visit http://localhost:4000/oauth/authorize to connect your account.
```

Visit that URL once in your browser, approve access on Mixcloud, and your token is written to `.env` and picked up immediately. You do not need to restart the server.

The sidecar also handles file uploads — the upload UI posts directly to `http://localhost:4000/upload`.

### HTTP — OAuth proxy

When `MIXCLOUD_CLIENT_ID` and `MIXCLOUD_CLIENT_SECRET` are set, the HTTP server acts as an OAuth proxy. Connecting MCP clients are redirected through Mixcloud's OAuth flow on first connection — no pre-shared token required. Each authenticated session gets its own Mixcloud token. All API calls and uploads use that token automatically.

The redirect URI registered in your Mixcloud app must be `<MCP_PUBLIC_URL>/auth/callback`.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

[GNU General Public License v3.0](LICENSE)
