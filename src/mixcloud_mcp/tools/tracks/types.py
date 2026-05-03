from pydantic import BaseModel

from mixcloud_mcp.tools.types import CloudcastUser, Tag


class Cloudcast(BaseModel):
    key: str
    name: str
    url: str
    slug: str
    description: str | None = None
    created_time: str
    updated_time: str
    audio_length: int
    play_count: int
    listener_count: int
    favorite_count: int
    comment_count: int
    repost_count: int
    tags: list[Tag] = []
    user: CloudcastUser
