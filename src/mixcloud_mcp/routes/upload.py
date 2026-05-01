"""Starlette route that receives multipart uploads from the MCP App UI
and forwards them to Mixcloud's upload API."""
import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from mixcloud_mcp.api.client import mixcloud_post_multipart
from mixcloud_mcp import upload_log


async def upload_endpoint(request: Request) -> JSONResponse:
    form = await request.form()

    mp3 = form.get("mp3")
    name = form.get("name")

    if not mp3 or not hasattr(mp3, "read"):
        return JSONResponse({"error": "mp3 file is required"}, status_code=400)
    if not name:
        return JSONResponse({"error": "name is required"}, status_code=400)

    mp3_bytes = await mp3.read()

    scalar_fields: dict[str, str] = {}
    for field in ("description", "unlisted", "publish_date", "disable_comments", "hide_stats"):
        val = form.get(field)
        if val:
            scalar_fields[field] = str(val)
    for i in range(5):
        val = form.get(f"tags-{i}-tag")
        if val:
            scalar_fields[f"tags-{i}-tag"] = str(val)
    for i in range(2):
        val = form.get(f"hosts-{i}-username")
        if val:
            scalar_fields[f"hosts-{i}-username"] = str(val)

    picture = form.get("picture")
    picture_bytes: bytes | None = None
    picture_filename: str | None = None
    if picture and hasattr(picture, "read"):
        picture_bytes = await picture.read()
        picture_filename = getattr(picture, "filename", None) or "picture.jpg"

    try:
        result = await mixcloud_post_multipart(
            mp3_bytes=mp3_bytes,
            filename=getattr(mp3, "filename", None) or "upload.mp3",
            data={**scalar_fields, "name": str(name)},
            picture_bytes=picture_bytes,
            picture_filename=picture_filename,
        )
        upload_log.record({
            "filename": getattr(mp3, "filename", None),
            "name": str(name),
            "mixcloud_url": result.get("url"),
            "status": "success" if result.get("result") else "error",
        })
        return JSONResponse(result)
    except httpx.HTTPStatusError as e:
        error_body = e.response.text
        upload_log.record({
            "filename": getattr(mp3, "filename", None),
            "name": str(name),
            "status": "error",
            "error": error_body,
        })
        return JSONResponse({"error": error_body}, status_code=502)
    except RuntimeError as e:
        return JSONResponse({"error": str(e)}, status_code=500)


route = Route("/upload", upload_endpoint, methods=["POST"])
