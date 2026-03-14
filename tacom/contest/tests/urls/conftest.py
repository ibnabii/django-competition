import importlib

import pytest

from .models.url_manager import UrlManager
from .utils.load_config import load_config
from .access_tester import AccessTester


@pytest.fixture(scope="session")
def url_config():
    return load_config()


@pytest.fixture(scope="session")
def url_manager(url_config):
    mgr = UrlManager(config=url_config)
    mgr.discover_urls()
    mgr.categorize()
    return mgr


@pytest.fixture
def data_provider(db, url_config):
    """Function-scoped: data is within the test transaction (rolled back after each test)."""
    provider_class_path = url_config.data_provider_class
    if not provider_class_path:
        from .data_provider import ContestDataProvider
        provider_class = ContestDataProvider
    else:
        module_path, class_name = provider_class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        provider_class = getattr(module, class_name)

    provider = provider_class()
    provider.setup()
    yield provider
    provider.teardown()


@pytest.fixture
def access_tester(url_manager, data_provider):
    from django.test import Client
    client = Client()
    client.raise_request_exception = False
    return AccessTester(
        url_manager=url_manager,
        data_provider=data_provider,
        client=client,
    )
