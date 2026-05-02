# Contributing to mixcloud-mcp

This project is built with [Claude Code](https://claude.ai/code) — contributions via vibe coding are welcome.

---

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`

---

## Setup

```bash
git clone https://github.com/nelsonra/mixcloud-mcp.git
cd mixcloud-mcp
uv sync
cp .env.example .env
```

Edit `.env` and add your credentials. There are two authentication paths — use whichever fits your workflow:

**Option A — OAuth (recommended, required for uploads):**

Register an app at [mixcloud.com/developers](https://www.mixcloud.com/developers/). Set the redirect URI to `http://localhost:4000/oauth/callback`, then add to `.env`:
```
MIXCLOUD_CLIENT_ID=your_client_id
MIXCLOUD_CLIENT_SECRET=your_client_secret
```

When you start the HTTP server or run stdio mode, the OAuth flow is handled automatically — see the sections below.

**Option B — Static token:**

Run the one-time OAuth CLI, approve in the browser, and the token is written to `.env`:
```bash
uv run mixcloud-mcp-oauth
```

---

## Running the server

**stdio (as Claude Desktop would run it):**
```bash
uv run mixcloud-mcp
```

If `MIXCLOUD_CLIENT_ID` and `MIXCLOUD_CLIENT_SECRET` are set, a sidecar starts on port 4000. Visit `http://localhost:4000/oauth/authorize` once to authenticate.

**HTTP server:**
```bash
MCP_PUBLIC_URL=http://localhost:8000 uv run mixcloud-mcp-http
```

`MCP_PUBLIC_URL` must be set when using OAuth — it tells Mixcloud where to redirect after login (`<MCP_PUBLIC_URL>/auth/callback`). For local dev, `http://localhost:8000` works as long as you registered that callback URI in your Mixcloud app.

Without OAuth, generate a static API key instead:
```bash
uv run mixcloud-mcp-keygen
# → add MCP_API_KEY=<output> to .env
uv run mixcloud-mcp-http
```

To skip auth entirely for quick local testing:
```bash
DISABLE_AUTH=true uv run mixcloud-mcp-http
```

---

## Testing tools with MCP Inspector

MCP Inspector gives you a browser UI to call tools and inspect responses interactively.

**stdio tools (no server needed):**
```bash
uv run fastmcp dev inspector src/mixcloud_mcp/server.py:mcp
```

**HTTP transport — start the server first, then open the inspector:**
```bash
MCP_PUBLIC_URL=http://localhost:8000 uv run mixcloud-mcp-http
```
```bash
uv run fastmcp dev inspector src/mixcloud_mcp/server.py:mcp
```
In the Inspector browser UI, switch transport to **Streamable HTTP** and enter `http://localhost:8000/mcp`.

---

## Testing the upload UI

The upload tool uses an embedded React UI rendered as an MCP App. To preview it locally:

**1. Start the HTTP server:**
```bash
MCP_PUBLIC_URL=http://localhost:8000 uv run mixcloud-mcp-http
```

**2. Start the MCP Apps preview in a second terminal:**
```bash
uv run fastmcp dev apps src/mixcloud_mcp/server.py
```

This opens a browser where you can call the `upload_cloudcast` tool — the upload form renders as an interactive UI. The form posts directly to `http://localhost:8000/upload` on the running server.

> Make sure `MIXCLOUD_ACCESS_TOKEN` is set in `.env` before testing uploads.

If you rebuild the React app (`npm run build` in `mcp-app/`), restart the HTTP server to pick up the new bundle.

---

## Testing the HTTP transport with Claude

The HTTP transport is intended for remote MCP clients. To test it end-to-end with Claude:

**1. Start the HTTP server with OAuth:**
```bash
MCP_PUBLIC_URL=http://localhost:8000 uv run mixcloud-mcp-http
```

Or with `DISABLE_AUTH=true` if you want to skip auth during initial testing:
```bash
DISABLE_AUTH=true uv run mixcloud-mcp-http
```

**2. Expose it publicly with ngrok:**
```bash
ngrok http 8000
```
ngrok prints a URL like `https://xxxx.ngrok-free.app`. Copy it.

**3. Add as a custom connector in Claude**

In Claude, go to **Settings → Connectors → Add custom connector** and enter:
```
https://xxxx.ngrok-free.app/mcp
```

With OAuth configured, Claude will prompt you to authenticate via Mixcloud on first connect. With `DISABLE_AUTH=true`, the tools are available immediately.

> When using ngrok for OAuth testing, set `MCP_PUBLIC_URL=https://xxxx.ngrok-free.app` and register that callback URI in your Mixcloud app.

---

## OAuth setup summary

| Mode | Redirect URI to register in Mixcloud app | Env var to set |
|---|---|---|
| stdio (local) | `http://localhost:4000/oauth/callback` | `UPLOAD_PORT=4000` (default) |
| HTTP (local dev) | `http://localhost:8000/auth/callback` | `MCP_PUBLIC_URL=http://localhost:8000` |
| HTTP (hosted) | `https://your-domain.com/auth/callback` | `MCP_PUBLIC_URL=https://your-domain.com` |
| HTTP (ngrok) | `https://xxxx.ngrok-free.app/auth/callback` | `MCP_PUBLIC_URL=https://xxxx.ngrok-free.app` |

---

## Project structure

```
mixcloud-mcp/
├── mcp-app/                  ← React upload UI (MCP App)
│   ├── src/
│   │   ├── mcp-app.tsx       ← upload form component
│   │   └── useMixcloudUploader.ts
│   └── dist/
│       └── mcp-app.html      ← self-contained built bundle (vite-plugin-singlefile)
├── docs/
│   └── adr/                  ← Architecture Decision Records
└── src/mixcloud_mcp/
    ├── server.py             ← FastMCP app — registers all tools and resources
    ├── stdio.py              ← stdio entry point (starts sidecar if OAuth configured)
    ├── http.py               ← HTTP entry point (Starlette wrapper, OAuth proxy, rate limiting)
    ├── auth.py               ← MixcloudOAuthProxy + MixcloudTokenVerifier
    ├── sidecar.py            ← lightweight sidecar for stdio mode (OAuth + upload)
    ├── keygen.py             ← mixcloud-mcp-keygen CLI
    ├── oauth.py              ← mixcloud-mcp-oauth CLI (one-time token flow, no credentials needed)
    ├── upload_log.py         ← in-memory upload result log (deque, last 20 entries)
    ├── api/
    │   └── client.py         ← Mixcloud API wrapper (injects token from session or env)
    ├── routes/
    │   └── upload.py         ← POST /upload — receives multipart form, forwards to Mixcloud
    └── tools/
        ├── search/           ← search_cloudcasts
        ├── tracks/           ← get_cloudcast
        ├── users/            ← get_user, get_user_cloudcasts, get_user_followers, get_user_following
        └── upload/           ← upload_cloudcast (MCP App UI tool)
```

Each tool category follows the same pattern:
- `__init__.py` — barrel that calls each tool's `register(mcp)`
- `types.py` — Pydantic models for the API response
- one file per tool (e.g. `get_user.py`) — implements and registers the tool

---

## Adding a new tool

1. Create a file in the relevant `tools/<category>/` folder
2. Define a `register(mcp: FastMCP) -> None` function with a `@mcp.tool()` decorated async function inside it
3. Add the register call to that category's `__init__.py`

Example:
```python
# src/mixcloud_mcp/tools/users/get_user_favorites.py
import json
from fastmcp import FastMCP
from mixcloud_mcp.api.client import mixcloud_get

def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_user_favorites(username: str, limit: int = 20) -> str:
        """Get a user's favourite mixes on Mixcloud."""
        clean = username.strip().strip("/").strip()
        raw = await mixcloud_get(f"/{clean}/favorites/", params={"limit": limit})
        return json.dumps(raw.get("data", []), indent=2)
```

Then add to `tools/users/__init__.py`:
```python
from .get_user_favorites import register as register_get_user_favorites

def register(mcp: FastMCP) -> None:
    ...
    register_get_user_favorites(mcp)
```

---

## Adding a new tool category

1. Create a new folder under `tools/` (e.g. `tools/playlists/`)
2. Add `__init__.py`, `types.py`, and your tool files
3. Import and call `register` in `server.py`

---

## Node → Python quick reference

If you're coming from a TypeScript/Node background:

| Node / TypeScript | Python |
|---|---|
| `npm install <pkg>` | `uv add <pkg>` |
| `npx` / `npm run` | `uv run` |
| `async/await` | `async/await` (same!) |
| `fetch()` | `httpx.AsyncClient()` |
| Zod schemas | Pydantic `BaseModel` |
| `z.object({...})` | `class Foo(BaseModel): ...` |
| `interface Foo {}` | `class Foo(BaseModel): ...` |
