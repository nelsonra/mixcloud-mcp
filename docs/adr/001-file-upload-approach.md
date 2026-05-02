# ADR 001: File Upload Approach — Custom HTTP Endpoint over FastMCP FileUpload Provider

**Date:** 2026-04-25
**Status:** Accepted
**Updated:** 2026-05-02 — sidecar note added (see ADR 002)

## Context

Mixcloud requires audio files to be uploaded via `POST /upload/` with a valid OAuth access token. Files are typically 300–400MB (2-hour= radio shows at 320kbps).

FastMCP (v3.2.0+) ships a built-in `FileUpload` provider that handles drag-and-drop UI, tool registration, and storage out of the box via subclassing.

## Decision

Use a custom HTTP endpoint (`POST /upload`) on the Starlette app, with a hand-built MCP App UI (HTML/JS using `@modelcontextprotocol/ext-apps`), rather than FastMCP's `FileUpload` provider.

## Reasons

**Memory overhead is prohibitive at our file sizes.**
FastMCP's `FileUpload` provider transfers file data as base64 through the MCP protocol before `on_store()` is called. Base64 encoding adds ~33% to the payload size. For a 400MB file, the base64 string alone is ~533MB in memory — before decoding back to bytes to forward to Mixcloud. At peak you hold both simultaneously.

With a direct HTTP POST, the file travels as raw bytes from the browser to the server. No encoding overhead, no double-buffering.

**The custom HTTP approach is already proven in another codebase.**
`libretime-mcp` uses the same pattern (see https://github.com/nelsonra/libretime-mcp for the node server implementation). The approach is understood and tested.

**Custom UI gives us full control.**
The MCP App HTML/JS component can be tailored to the Mixcloud upload workflow: mix name field, tags, description, cover art, upload progress. FastMCP's `FileUpload` UI is a generic drop zone with limited customisation.

## Consequences

- Requires a `mcp-app/` subfolder with a Node/Vite build step to produce the bundled HTML
- The Python server registers the HTML as a `ui://` resource and serves it to Claude Desktop
- The `POST /upload` Starlette route handles multipart form data and forwards to Mixcloud
- An upload log (`upload_log.py`) tracks results so Claude can read them back via a `list_files` tool

## Alternatives considered

**FastMCP `FileUpload` provider** — rejected due to base64 memory overhead at 300–400MB file sizes. Well-suited for smaller files (documents, images) where the 33% overhead is acceptable.

## stdio transport note

In stdio mode there is no HTTP server, so the `POST /upload` endpoint needs a sidecar process. See ADR 002 for how the sidecar is started and how it relates to OAuth token acquisition.
