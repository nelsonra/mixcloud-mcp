from pydantic import BaseModel

from mixcloud_mcp.tools.types import CloudcastUser, Tag  # noqa: F401


class CloudcastResult(BaseModel):
    key: str
    name: str
    url: str
    slug: str
    created_time: str
    audio_length: int
    play_count: int
    listener_count: int
    tags: list[Tag] = []
    user: CloudcastUser


class SearchResponse(BaseModel):
    data: list[CloudcastResult]
