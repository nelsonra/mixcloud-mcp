from pydantic import BaseModel


class UserSummary(BaseModel):
    key: str
    name: str
    username: str
    url: str


class UserListResponse(BaseModel):
    data: list[UserSummary]


class User(BaseModel):
    key: str
    name: str
    username: str
    url: str
    biog: str | None = None
    created_time: str
    follower_count: int
    following_count: int
    cloudcast_count: int
    city: str | None = None
    country: str | None = None
    is_pro: bool = False
    is_premium: bool = False
