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

The HTTP transport exposes the server over the network so remote MCP clients (Claude.ai, Claude Desktop configured with a URL) can connect to it.

### 1. Register a Mixcloud OAuth app

Go to [mixcloud.com/developers](https://www.mixcloud.com/developers/) and create an app. You will get a **Client ID** and **Client Secret**.

Set the redirect URI to your server's public URL plus `/oauth/callback`:

```
https://your-server.example.com/oauth/callback
```

If you are running locally with ngrok, use your ngrok URL instead (see step 3).

### 2. Configure your environment

Create a `.env` file (or set these as environment variables):

```bash
MIXCLOUD_CLIENT_ID=your_client_id
MIXCLOUD_CLIENT_SECRET=your_client_secret
MCP_PUBLIC_URL=https://your-server.example.com   # public HTTPS URL — no port, no trailing slash
MCP_API_KEY=your_secret_key                       # protects the MCP endpoint; generate with mixcloud-mcp-keygen
```

> **`MCP_PUBLIC_URL` is required.** It must be HTTPS and match the domain you registered as the redirect URI in your Mixcloud app. If you are running locally via ngrok, this is your ngrok URL (e.g. `https://xxxx.ngrok-free.app`). Do not include a port number — ngrok handles port mapping for you.

> **Optional:** if you already have a Mixcloud access token, set `MIXCLOUD_ACCESS_TOKEN` and skip step 4.

### 3. Start the server

```bash
uvx mixcloud-mcp-http
```

On startup you will see a line like:

```
[http] No Mixcloud token — visit https://your-server.example.com/oauth/authorize to enable uploads.
```

If you are running locally, expose the server first with ngrok:

```bash
ngrok http 8000
```

Use the ngrok HTTPS URL as `MCP_PUBLIC_URL` and make sure the same URL is registered as the redirect URI in your Mixcloud app.

### 4. Authenticate with Mixcloud

Open `https://your-server.example.com/oauth/authorize` in your browser and approve access. The server logs:

```
[http] Mixcloud token stored — upload tool is now authenticated.
```

The token is held in memory for the lifetime of the process. To persist it across restarts, copy the token into `MIXCLOUD_ACCESS_TOKEN` in your `.env`.

### 5. Add the connector in Claude

In Claude, go to **Settings → Connectors → Add custom connector** and enter:

```
https://your-server.example.com/mcp
```

> The URL must end in `/mcp`. The base URL alone will not work.

Read-only tools (search, browse, get user) are available immediately. The upload tool becomes available once you have authenticated with Mixcloud in step 4.

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
| `MCP_API_KEY` | — | Bearer token protecting the MCP endpoint. Generate with `mixcloud-mcp-keygen`. |
| `MCP_PORT` | `8000` | HTTP server port. |
| `MCP_PUBLIC_URL` | `http://localhost:<MCP_PORT>` | Public base URL of the server. **Required for browser OAuth** — Mixcloud redirects back to `<MCP_PUBLIC_URL>/oauth/callback`. |
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

### HTTP — server-level authentication

The HTTP server authenticates to Mixcloud once and shares that token across all connected MCP clients. There is no per-user token — whoever authenticates first sets the token for the lifetime of the process.

You can provide the token two ways (see the Quickstart above): pre-set `MIXCLOUD_ACCESS_TOKEN` in your environment, or visit `/oauth/authorize` in a browser after starting the server. In both cases the read-only tools are always available to any client that has the `MCP_API_KEY`; uploads become available once a Mixcloud token is present.

The redirect URI registered in your Mixcloud app must be `<MCP_PUBLIC_URL>/oauth/callback`.

---

## Future ideas

- **Per-user sessions in HTTP mode** — currently all MCP clients share a single Mixcloud token. A session layer would let each user authenticate independently and upload to their own Mixcloud account.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

[GNU General Public License v3.0](LICENSE)
