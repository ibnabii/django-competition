from pydantic import BaseModel

from .config import Config


class Url(BaseModel):
    url_route: str
    name: str
    name_space: str = ""


class UrlManager(BaseModel):
    urls: list[Url]
    initial_urls: list[str]
    config: Config
