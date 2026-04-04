# Contributing to mixcloud-mcp

This project is built with [Claude Code](https://claude.ai/code) — contributions via vibe coding are welcome.

---

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`

---

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/mixcloud-mcp.git
cd mixcloud-mcp
uv sync
cp .env.example .env
```

---

## Running the server

**Interactive inspector (best for development):**
```bash
uv run fastmcp dev inspector src/mixcloud_mcp/server.py:mcp
```
Opens a browser UI where you can call tools and inspect responses in real time.

**stdio (as Claude Desktop would run it):**
```bash
uv run python -m mixcloud_mcp.stdio
```

**HTTP server:**
```bash
uv run python -m mixcloud_mcp.http
```

---

## Project structure

```
src/mixcloud_mcp/
├── server.py        ← FastMCP app — registers all tools
├── stdio.py         ← stdio entry point
├── http.py          ← HTTP entry point
├── api/
│   └── client.py    ← Mixcloud API wrapper (all HTTP calls go here)
└── tools/
    ├── search/      ← search tools
    ├── tracks/      ← cloudcast/mix tools
    └── users/       ← user profile tools
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
