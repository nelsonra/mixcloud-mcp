# Plan: Mixcloud File Upload with MCP App UI

## Context

The MCP server currently only supports public read-only tools. This plan adds a file upload workflow: a browser-based file picker (MCP App) that renders inline in Claude Desktop, a direct HTTP endpoint to receive the file and forward it to Mixcloud, and a companion tool to read back results so Claude can continue the conversation.

> **Auth:** Get a token from https://www.mixcloud.com/developers/ and set `MIXCLOUD_ACCESS_TOKEN` in `.env`. OAuth deferred.
>
> **Why not FastMCP's built-in `FileUpload` provider:** See [ADR 001](docs/adr/001-file-upload-approach.md). Files are 300–400MB — base64 overhead through the MCP protocol is not acceptable at this size.

---

## Status

**Session 2 (2026-05-01/02) — OAuth, HTTP server infrastructure fixes, upload tested end-to-end.**

### What was built / fixed

#### `oauth.py` — new CLI command: `mixcloud-mcp-oauth`

One-time OAuth flow to obtain a Mixcloud access token and write it to `.env`. Starts a temporary local HTTP server on a random port, opens the browser to Mixcloud's auth page, captures the authorization code, exchanges it for an access token, and writes `MIXCLOUD_ACCESS_TOKEN` to `.env` using `dotenv.set_key`. Registered in `pyproject.toml` as `mixcloud-mcp-oauth`.

Key notes:
- Mixcloud does not support state parameter — removed CSRF check to avoid false-positive mismatch errors
- Token exchange uses GET, not POST (unusual but valid OAuth 2.0)
- `MIXCLOUD_CLIENT_ID` and `MIXCLOUD_CLIENT_SECRET` must be set in `.env` first (from mixcloud.com/developers)

#### `http.py` — critical infrastructure fixes

**`BaseHTTPMiddleware` → pure ASGI middleware.** The original `McpMiddleware` used Starlette's `BaseHTTPMiddleware` which buffers entire response bodies before returning them. This broke FastMCP's streamable-http SSE transport (the `StreamableHTTPSessionManager` task group was never initialized), causing 500 errors on every MCP connection. Replaced with a pure ASGI middleware class (`__call__(scope, receive, send)`) that passes streaming responses through untouched.

**Lifespan wiring.** FastMCP's HTTP transport requires `lifespan=mcp_starlette.lifespan` to be passed to the parent Starlette app constructor. Without it, the session manager task group is not initialized and every request fails with `RuntimeError: Task group is not initialized. Make sure to use run()`.

**CORS middleware.** The React upload UI runs in an iframe sandbox on a different origin. Browser blocks `fetch()` to `/upload` without `Access-Control-Allow-Origin`. Added `CORSMiddleware` as the outermost middleware layer — it must be outermost so browser preflight OPTIONS requests are handled before auth runs (otherwise preflight gets 401 and the browser never sends the actual upload). Origin configurable via `CORS_ORIGIN` env var, defaults to `*`.

#### Upload tool registration restructured

`tools/upload/__init__.py` created as a dedicated barrel for upload tools. The `upload_cloudcast` implementation stays in `tools/tracks/upload_cloudcast.py` but is registered via the upload barrel, not the tracks barrel. Tool is now unconditionally registered (no `MIXCLOUD_ACCESS_TOKEN` guard at startup) — the guard belongs at upload time, not at server startup, and the conditional registration was preventing `fastmcp dev apps` from finding the UI tool.

`load_dotenv()` added to `server.py` so env vars are loaded when `fastmcp dev apps src/mixcloud_mcp/server.py` runs directly (bypasses entry point `load_dotenv` calls in `http.py` / `stdio.py`).

#### `api/client.py` — upload response logging + empty body fix

`response.json() if response.content else {}` guards both GET and POST multipart responses against empty bodies. Mixcloud returns HTTP 200 with an empty body on successful upload — parsing that as JSON raises `JSONDecodeError`. Added `[mixcloud upload] <status>\n<pretty-printed body>` logging to stderr on every upload response.

#### `mcp-app/src/useMixcloudUploader.ts` — dev preview compatibility

`app.updateModelContext()` wrapped in `.catch(() => {})`. This method is only available in a real MCP host (Claude Desktop). `fastmcp dev apps` does not implement it and returns `-32601 Method not found`, which was surfacing as an error in the preview UI after a successful upload. Swallowing the error lets the success screen render normally in dev.

#### CONTRIBUTING.md updated

Added sections for: MCP Inspector usage (stdio and HTTP variants), upload UI testing with `fastmcp dev apps`, OAuth setup (`mixcloud-mcp-oauth`). Updated project structure to include `mcp-app/`, `oauth.py`, `routes/`, and `tools/upload/`.

### Upload end-to-end test result

Upload reached Mixcloud and returned HTTP 200 with empty body (Mixcloud's success indicator). File did not appear in account — suspected free account limitation. Awaiting test with a Pro account.

---

**Session 1 (2026-04-25/26) — HTTP mode complete, stdio sidecar deferred.**

### What was built

#### MCP App UI (`mcp-app/`)

Built using the `mcp-apps` Claude Code plugin (`/create-mcp-app`). Separate subfolder with its own `package.json`, built with Vite + `vite-plugin-singlefile`. Output is a single self-contained HTML file at `mcp-app/dist/mcp-app.html` — Python reads this from disk and serves it as a `ui://` resource.

The UI is React + TypeScript. Deliberately different from the libretime-mcp upload UI:
- Fields grouped into section cards (Audio, Details, Tags, Options, Advanced PRO) rather than a flat list
- Dynamic tag inputs — start with 1, add up to 5 with +/× buttons
- PRO-only fields (publish date, disable comments, hide stats, hosts) live in a distinct "Advanced PRO" section with a yellow badge
- Character counter on description (1000 char limit)
- Client-side file size validation (4 GB MP3, 10 MB picture)
- PowerFM branding: "powered by" + logo in header, linking to powerfm.org

Supports all Mixcloud upload fields: `mp3`, `name`, `picture`, `description`, `tags-X-tag` (0–4), `unlisted`, `publish_date`, `disable_comments`, `hide_stats`, `hosts-X-username` (0–1). Sections not included yet.

**Build:**
```bash
cd mcp-app && npm install && npm run build
# → mcp-app/dist/mcp-app.html (single file, ~530 KB)
```

#### Python server changes

**`api/client.py`** — added `mixcloud_post_multipart()`. Sends multipart/form-data to `https://upload.mixcloud.com/upload/`. httpx uses a 3-tuple `(filename, bytes, content_type)` for file fields and `data={}` for scalar fields — never set `Content-Type` manually.

**`upload_log.py`** — module-level `deque(maxlen=20)` singleton. `record(entry)` prepends, `recent(n)` slices. No cleanup needed — `deque(maxlen=N)` drops the oldest entry automatically when full.

**`routes/upload.py`** — Starlette route at `POST /upload`. Parses multipart form, collects all scalar fields (tags, hosts, etc.), reads file bytes, calls `mixcloud_post_multipart`, records to `upload_log`, returns JSON. Exported as `route = Route("/upload", ...)` so `http.py` can import and mount it cleanly.

**`http.py`** — restructured. Previously the upload handler would have been inline here, making the file large. Instead: imports `upload_route` from `routes/upload.py` and mounts it alongside the FastMCP Starlette app using `Starlette(routes=[upload_route, Mount("/", app=mcp_starlette)])`. `McpMiddleware` applies to all routes including `/upload`, so auth runs before the handler.

**`tools/tracks/upload_cloudcast.py`** — replaced broken placeholder. Uses FastMCP's custom HTML MCP App pattern:
- `@mcp.tool(app=AppConfig(resource_uri=RESOURCE_URI))` — links the tool to the UI resource
- Tool returns `upload_url` + `upload_token` as JSON; the UI reads these from `ontoolresult`
- `@mcp.resource(RESOURCE_URI, app=AppConfig(csp=ResourceCSP(connect_domains=[origin])))` — serves the built HTML; CSP allows `fetch()` to the upload origin (without this the iframe sandbox blocks the request entirely)
- HTML path computed from `__file__`: `Path(__file__).parents[4] / "mcp-app" / "dist" / "mcp-app.html"`

**`tools/tracks/__init__.py`** — fixed broken barrel. Was missing `import os` and the import for `register_upload_cloudcast`. Now conditionally registers the upload tool only when `MIXCLOUD_ACCESS_TOKEN` is set.

### How the FastMCP custom HTML pattern works

Two things must be registered together:

1. A **tool** decorated with `app=AppConfig(resource_uri="ui://...")` — this tells the host "when this tool is called, render that UI resource alongside the result"
2. A **resource** at that `ui://` URI decorated with `app=AppConfig(csp=...)` — serves the single-file HTML; `csp.connect_domains` tells the host to allow `fetch()` from the iframe to that origin

The tool result carries `upload_url` and `upload_token`. The iframe reads them from `app.ontoolresult`, then POSTs the file directly over HTTP — the file never touches the MCP protocol.

Reference: https://gofastmcp.com/apps/low-level

---

## What's still to do

### `list_uploads` tool (small, next session)

Reads from `upload_log.recent()` and returns JSON so Claude can see results and continue the conversation.

```python
# tools/tracks/list_uploads.py
@mcp.tool()
async def list_uploads(limit: int = 5) -> str:
    """Return the most recent Mixcloud upload results."""
    return json.dumps(upload_log.recent(limit), indent=2)
```

Register it alongside `upload_cloudcast` in `tools/tracks/__init__.py` (same `MIXCLOUD_ACCESS_TOKEN` guard).

### stdio sidecar (future)

For Claude Desktop (stdio mode), the MCP App UI still needs an HTTP server to POST the file to — the MCP protocol is the only transport in stdio mode and it can't carry raw file bytes efficiently.

The plan: run a lightweight sidecar HTTP server on a configurable port (`UPLOAD_PORT`, default 4000) that starts alongside the stdio process. The `upload_cloudcast` tool would return `upload_url: http://localhost:4000/upload`. The sidecar handles the same `/upload` logic as `routes/upload.py`.

This makes mixcloud-mcp useful as a local Claude Desktop tool without needing to host the full HTTP server — relevant because Mixcloud is a widely used platform and many users will want to run this locally without self-hosting a server.

Approach: start the sidecar in `stdio.py` using `asyncio` or a background thread before handing off to FastMCP's stdio transport. Can reuse `routes/upload.py` by mounting it in a minimal Starlette app.

### Tests

```python
# tests/routes/test_upload.py
# Mock mixcloud_post_multipart + upload_log.record
# Test: missing mp3 → 400, missing name → 400, successful upload → 200 + log entry, Mixcloud error → 502
```

Follow the existing `patch` + `AsyncMock` pattern from `test_search.py`.

### Publishing

The built `mcp-app/dist/mcp-app.html` must be committed to git and included in the PyPI wheel — it is not generated at install time. The publish checklist must always run the frontend build first.

**`pyproject.toml` — include the built HTML in the wheel:**

The wheel currently packages only `src/mixcloud_mcp` (`[tool.hatch.build.targets.wheel] packages = ["src/mixcloud_mcp"]`). The HTML lives outside that tree at `mcp-app/dist/mcp-app.html`. Two options:

- **Option A (recommended):** Copy the built HTML into the Python package tree as part of the build step, e.g. `src/mixcloud_mcp/static/mcp-app.html`, update `HTML_PATH` in `upload_cloudcast.py` accordingly, and let hatchling include it automatically.
- **Option B:** Use `[tool.hatch.build.targets.wheel] artifacts` to include the `mcp-app/dist/` path explicitly.

Either way, `HTML_PATH` in `upload_cloudcast.py` must resolve correctly both when running from source (`uv run`) and from an installed wheel (`uvx`).

**Publish checklist (run in order):**

```bash
# 1. Build the MCP App UI
cd mcp-app && npm install && npm run build && cd ..

# 2. Copy built HTML into the Python package (if using Option A)
cp mcp-app/dist/mcp-app.html src/mixcloud_mcp/static/mcp-app.html

# 3. Run tests
uv run pytest

# 4. Bump version in pyproject.toml

# 5. Build and publish
uv build
uv publish
```

Committing `mcp-app/dist/mcp-app.html` to git means contributors cloning the repo don't need Node to run the server — the built asset is always present. Only contributors changing the UI need to rebuild it.

---

## End-to-end verification checklist

1. `cd mcp-app && npm run build` — produces `dist/mcp-app.html`
2. Set `MIXCLOUD_ACCESS_TOKEN` and `MCP_API_KEY` in `.env`
3. `uv run python -m mixcloud_mcp.http` — server starts, prints `/upload` endpoint line
4. `upload_cloudcast` appears in tool list regardless of token — missing token surfaces as error at upload time, not at startup
5. `upload_cloudcast` returns `upload_url`/`upload_token` (token is `null` when auth disabled)
6. In Claude Desktop (HTTP mode), call `upload_cloudcast` — file picker UI renders inline
7. Upload a test MP3 — Mixcloud receives it, upload log has an entry
8. Call `list_uploads` — Claude sees the result and can continue the conversation
9. `uv run pytest` — all tests pass

---

## Architecture

```
Claude Desktop renders MCP App iframe
        ↓
MCP App UI (browser)  →  POST /upload (HTTP multipart, raw bytes)  →  routes/upload.py
                                                                              ↓
                                                              mixcloud_post_multipart()
                                                                              ↓
                                                                   upload_log.record(result)
                                                                              ↓
                                               list_uploads tool  ←  Claude reads result, continues conversation
```

The file travels as raw bytes over HTTP — no base64, no MCP protocol overhead.
