# ADR 002: OAuth Strategy — Different Approaches for HTTP and stdio Transports

**Date:** 2026-05-02
**Status:** Accepted

## Context

Mixcloud requires an OAuth 2.0 access token for write operations (uploads, favorites, etc.).
The server supports two transports — HTTP (hosted, remote clients) and stdio (local, Claude Desktop) — and they have fundamentally different authentication needs:

- **HTTP transport**: Claude Desktop connects to a remote server over HTTP. Any number of users could connect; each should authenticate individually.
- **stdio transport**: Claude Desktop spawns the server as a local subprocess. There is effectively one user — the machine owner. No HTTP auth layer exists at the MCP protocol level.

FastMCP 3.2.0 ships `OAuthProxy`, which acts as a DCR-compliant OAuth authorization server that proxies to an upstream provider. It is designed for authenticating **MCP clients** (e.g. Claude Desktop) to the **MCP server** over HTTP.

## Decision

Use two different mechanisms — one per transport.

### HTTP transport: `MixcloudOAuthProxy`

`OAuthProxy` is subclassed as `MixcloudOAuthProxy` (see `auth.py`) to handle two Mixcloud-specific quirks:

1. **GET token exchange**: Mixcloud's token endpoint uses `GET` with query parameters instead of the standard `POST` with form body. Handled by passing `extra_token_params={"method": "GET"}` to the proxy constructor — this is spread into authlib's `fetch_token(**...)` call.

2. **URL-encoded token response**: Mixcloud returns `access_token=xxx` as plain text instead of a JSON object. Handled by registering an `access_token_response` compliance hook on the `AsyncOAuth2Client` that re-wraps the response as JSON before authlib parses it.

When both `MIXCLOUD_CLIENT_ID` and `MIXCLOUD_CLIENT_SECRET` are set, `http.py` builds a `MixcloudOAuthProxy` and passes it to `mcp.http_app(auth=...)`. FastMCP then:
- Exposes `/.well-known/oauth-authorization-server` and `/authorize` / `/token` / `/auth/callback` / `/consent` routes
- Issues short-lived FastMCP JWTs to authenticated MCP clients
- Stores the upstream Mixcloud token encrypted in a local file store

Tools access the Mixcloud token via `get_access_token().token`, which retrieves it from the proxy's storage for the current request session. The `upload_cloudcast` tool forwards it to the `/upload` endpoint as a Bearer token; `/upload` passes it directly to Mixcloud's upload API.

### stdio transport: sidecar (`sidecar.py`)

`OAuthProxy` cannot be used here because stdio mode has no HTTP MCP clients — Claude Desktop communicates via stdin/stdout pipes. There is no per-request OAuth context and `get_access_token()` always returns `None`.

Instead, a lightweight sidecar HTTP server is started in a background daemon thread before `mcp.run()`. The sidecar exposes two routes:

- `GET /oauth/authorize` — redirects the user's browser to Mixcloud's authorization page
- `GET /oauth/callback` — exchanges the authorization code for a token (Mixcloud's GET-based flow), writes `MIXCLOUD_ACCESS_TOKEN` to `.env` and `os.environ`, and shows a success page

After the one-time browser flow completes, tools read `MIXCLOUD_ACCESS_TOKEN` from the environment. The sidecar also hosts `POST /upload` so the MCP App UI can POST files directly without going through the stdio pipe.

The sidecar starts automatically when `MIXCLOUD_CLIENT_ID` and `MIXCLOUD_CLIENT_SECRET` are set. If `MIXCLOUD_ACCESS_TOKEN` is not yet in the environment at startup, the server prints the authorize URL to stderr so the user knows to visit it.

## Reasons for the split

- `OAuthProxy` requires an HTTP layer to issue and validate JWTs. stdio has none.
- In stdio mode the Mixcloud token is shared across the whole session (one server, one user), so per-request token storage adds no value. A single env var is sufficient.
- The sidecar approach reuses `routes/upload.py` unchanged. Keeping `/upload` as a standalone Starlette route means the same code runs in both HTTP mode (as part of the main app) and stdio mode (in the sidecar).
- Token persistence to `.env` follows the same pattern established by the original `mixcloud-mcp-oauth` CLI (`oauth.py`), replacing it for users who configure the sidecar.

## Consequences

- `MIXCLOUD_CLIENT_ID` and `MIXCLOUD_CLIENT_SECRET` are required for OAuth in either mode. Without them, `MIXCLOUD_ACCESS_TOKEN` must be set manually (via `mixcloud-mcp-oauth` or directly in `.env`).
- The sidecar listens on `UPLOAD_PORT` (default `4000`). This port must be free. `MCP_PUBLIC_URL` overrides the base URL if the sidecar is behind a proxy.
- `oauth.py` (`mixcloud-mcp-oauth` CLI) remains available as a fallback for users who prefer a one-shot token acquisition without running the server at all.
- Upload in stdio mode requires the sidecar — without it, `/upload` has nowhere to receive the file. Tools still register unconditionally; the error surfaces at upload time, not at startup.
- The `upload_cloudcast` tool uses `get_access_token().token` in HTTP OAuth mode and `os.getenv("MIXCLOUD_ACCESS_TOKEN")` in all other modes, so the tool code is the same and the routing is determined at call time.

## Alternatives considered

**Single `OAuthProxy` for both transports** — rejected. stdio has no HTTP auth layer; there is no mechanism to pass FastMCP JWTs to the tools without one. A hybrid approach would require re-implementing the JWT validation inside the stdio process, adding significant complexity for no benefit over a simple env var.

**`mixcloud-mcp-oauth` CLI for stdio, nothing else** — retained as a supported path. The sidecar integrates the flow, but users can still run the CLI once and set the env var manually if they prefer not to expose a local HTTP port.

**FastMCP built-in `OAuthProxy` with no subclassing** — not viable. `fetch_token` defaults to POST and `parse_response_token` always calls `resp.json()`. Neither can be configured without subclassing or compliance hooks.
