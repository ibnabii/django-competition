from ..models.url_manager import UrlManager
from .load_config import load_config


def get_url_manager(path=None) -> UrlManager:
    config = load_config(path)
    mgr = UrlManager(config=config)
    mgr.discover_urls()
    mgr.categorize()
    return mgr
