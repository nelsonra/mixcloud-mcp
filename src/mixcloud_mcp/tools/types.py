from pydantic import BaseModel


class Tag(BaseModel):
    key: str
    name: str
    url: str


class CloudcastUser(BaseModel):
    key: str
    name: str
    username: str
    url: str
