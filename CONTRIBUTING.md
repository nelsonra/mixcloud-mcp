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

Generate a secure API key for HTTP transport and add it to `.env`:

```bash
uv run mixcloud-mcp-keygen
```

To run the HTTP server locally without needing a key, set `DISABLE_AUTH=true` in your `.env`. Never use this in production.

**Optional — Mixcloud OAuth (required for upload and authenticated tools):**

Add your app credentials from [mixcloud.com/developers](https://www.mixcloud.com/developers/) to `.env`:
```
MIXCLOUD_CLIENT_ID=your_client_id
MIXCLOUD_CLIENT_SECRET=your_client_secret
```

Then run the one-time OAuth flow — it opens a browser, you approve, and the token is written to `.env` automatically:
```bash
uv run mixcloud-mcp-oauth
```

Restart the server after this to pick up the new token.

---

## Running the server

**stdio (as Claude Desktop would run it):**
```bash
uv run mixcloud-mcp
```

**HTTP server:**
```bash
uv run mixcloud-mcp-http
```

**Generate an API key for HTTP auth:**
```bash
uv run mixcloud-mcp-keygen
```

---

## Testing tools with MCP Inspector

MCP Inspector gives you a browser UI to call tools and inspect responses interactively.

**stdio tools (no server needed):**
```bash
uv run fastmcp dev inspector src/mixcloud_mcp/server.py:mcp
```

**HTTP transport:**

Start the server in one terminal, then open the inspector in another:
```bash
uv run mixcloud-mcp-http
```
```bash
uv run fastmcp dev inspector src/mixcloud_mcp/server.py:mcp
```
In the Inspector browser UI, switch transport to **Streamable HTTP** and enter `http://localhost:3000/mcp` (or your configured port).

---

## Testing the upload UI

The upload tool uses an embedded React UI rendered as an MCP App. To preview it locally:

**1. Start the HTTP server** (the upload form POSTs to its `/upload` route):
```bash
uv run mixcloud-mcp-http
```

**2. Start the MCP Apps preview** in a second terminal:
```bash
uv run fastmcp dev apps src/mixcloud_mcp/server.py
```

This opens a browser where you can call the `upload_cloudcast` tool — the upload form renders as an interactive UI in the conversation. The form submits directly to `http://localhost:PORT/upload` on the running HTTP server.

> Make sure `MIXCLOUD_ACCESS_TOKEN` is set in `.env` (run `mixcloud-mcp-oauth` first) — uploads will fail without it.

If you rebuild the React app (`npm run build` in `mcp-app/`), restart the HTTP server to pick up the new bundle.

---

## Testing the HTTP transport with Claude

The HTTP transport is intended for server-to-server use. To test it end-to-end with Claude:

**1. Disable auth in `.env` for local testing**
```
DISABLE_AUTH=true
```

**2. Start the HTTP server**
```bash
uv run mixcloud-mcp-http
```

**3. Expose it publicly with ngrok**
```bash
ngrok http 8000
```
ngrok prints a URL like `https://xxxx.ngrok-free.app`. Copy it.

**4. Add as a custom connector in Claude**

In Claude, go to **Settings → Connectors → Add custom connector** and enter:
```
https://xxxx.ngrok-free.app/mcp
```

The tools will be available in Claude immediately. Remember to revert `DISABLE_AUTH` and use a proper `MCP_API_KEY` when deploying to production.

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
└── src/mixcloud_mcp/
    ├── server.py             ← FastMCP app — registers all tools and resources
    ├── stdio.py              ← stdio entry point
    ├── http.py               ← HTTP entry point (Starlette wrapper, auth, rate limiting)
    ├── keygen.py             ← mixcloud-mcp-keygen CLI
    ├── oauth.py              ← mixcloud-mcp-oauth CLI (one-time Mixcloud auth flow)
    ├── api/
    │   └── client.py         ← Mixcloud API wrapper (all HTTP calls go here)
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
