# Mixcloud MCP Server

A [FastMCP](https://github.com/jlowin/fastmcp) server that bridges the [Mixcloud API](https://www.mixcloud.com/developers/) to AI assistants via the Model Context Protocol (MCP).

Supports both **stdio** (local, Claude Desktop) and **HTTP** (hosted, remote MCP clients).

---

## What this project does

Exposes Mixcloud data — mixes, users, search — as MCP tools that any MCP-compatible AI client can call. Think of it as a translation layer: Claude asks "search for deep house mixes", this server calls the Mixcloud API and returns structured results.

---

## Tech stack

- **Python 3.14+**
- **[FastMCP](https://github.com/jlowin/fastmcp)** — Python MCP server framework (think of it as the Python equivalent of `@modelcontextprotocol/sdk`)
- **[httpx](https://www.python-httpx.org/)** — async HTTP client (replaces `fetch()`)
- **[Pydantic](https://docs.pydantic.dev/)** — data validation and schemas (replaces Zod)
- **[uv](https://docs.astral.sh/uv/)** — package manager (replaces npm)

---

## Folder structure

```
mixcloud-mcp/
├── CLAUDE.md               ← you are here
├── PLAN.md                 ← current build status and roadmap
├── .env.example            ← copy to .env and fill in your keys
├── pyproject.toml          ← project config + dependencies (like package.json)
├── uv.lock                 ← lockfile (like package-lock.json) — commit this
│
├── src/
│   └── mixcloud_mcp/
│       ├── __init__.py     ← marks this folder as a Python package
│       ├── server.py       ← creates the FastMCP app and registers all tools
│       ├── stdio.py        ← entry point: stdio transport (Claude Desktop / local)
│       ├── http.py         ← entry point: HTTP transport (hosted / remote clients)
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   └── client.py   ← thin httpx wrapper for the Mixcloud REST API
│       │
│       └── tools/          ← one sub-folder per tool category
│           ├── __init__.py
│           ├── search/
│           │   ├── __init__.py             ← register() barrel — wires tools to mcp
│           │   ├── types.py                ← Pydantic models for this category
│           │   └── search_cloudcasts.py    ← tool implementation
│           ├── tracks/
│           │   ├── __init__.py
│           │   ├── types.py
│           │   └── get_cloudcast.py
│           └── users/
│               ├── __init__.py
│               ├── types.py
│               └── get_user.py
│
├── tests/
│   ├── __init__.py
│   └── tools/
│       ├── __init__.py
│       ├── test_search.py
│       ├── test_tracks.py
│       └── test_users.py
│
└── playground/             ← scratch space for experiments, not production code
```

---

## Getting started

```bash
# 1. Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv sync

# 3. Copy env file and add your Mixcloud credentials
cp .env.example .env

# 4. Run in dev mode (stdio inspector — great for testing tools interactively)
uv run fastmcp dev src/mixcloud_mcp/server.py

# 5. Run as stdio server (for Claude Desktop)
uv run python -m mixcloud_mcp.stdio

# 6. Run as HTTP server (for hosted/remote clients)
uv run python -m mixcloud_mcp.http
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `MIXCLOUD_ACCESS_TOKEN` | No | OAuth token for authenticated requests. Public data works without it. |
| `MCP_API_KEY` | HTTP only | Bearer token to protect the HTTP endpoint |
| `MCP_PORT` | No | HTTP server port (default: `8000`) |

---

## How tools are structured

Each tool lives in its own file and exports a single `register(mcp)` function:

```python
# src/mixcloud_mcp/tools/search/search_cloudcasts.py
from fastmcp import FastMCP

def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def search_cloudcasts(query: str, limit: int = 20) -> str:
        """Search Mixcloud for mixes by keyword."""
        ...
```

The category `__init__.py` acts as a barrel — it calls each tool's `register()`:

```python
# src/mixcloud_mcp/tools/search/__init__.py
from fastmcp import FastMCP
from .search_cloudcasts import register as register_search_cloudcasts

def register(mcp: FastMCP) -> None:
    register_search_cloudcasts(mcp)
```

`server.py` wires everything together:

```python
# src/mixcloud_mcp/server.py
from fastmcp import FastMCP
from .tools.search import register as register_search

mcp = FastMCP("Mixcloud MCP Server")
register_search(mcp)
```

---

## Node → Python quick reference

If you're coming from the `libretime-mcp` Node project or are more familiar with TypeScript:

| Node / TypeScript | Python |
|---|---|
| `npm install` | `uv sync` |
| `npm install <pkg>` | `uv add <pkg>` |
| `npx` / `npm run` | `uv run` |
| `package.json` | `pyproject.toml` |
| `McpServer` + `registerTool` | `FastMCP` + `@mcp.tool()` |
| `StdioServerTransport` | `mcp.run()` (stdio is default) |
| `StreamableHTTPServerTransport` | `mcp.run(transport="streamable-http")` |
| Zod schemas | Pydantic `BaseModel` |
| `fetch()` | `httpx.AsyncClient()` |
| `async/await` | `async/await` (same!) |
| `z.object({...})` | `class Foo(BaseModel): ...` |
| `toolText(data)` helper | FastMCP handles response shape for you |

---

## Contributing

This project is built with Claude Code — feel free to vibe code your contributions.

When opening a new Claude Code session on this repo:
1. Claude will read this file automatically for project context
2. Check `PLAN.md` for current build status and what's next
3. The `playground/` folder is safe to experiment in — nothing there is wired up

Useful prompts to get started:
- _"What tools are implemented so far?"_
- _"Implement the search_cloudcasts tool following the existing pattern"_
- _"Add a new tool category for playlists"_
