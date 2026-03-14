import pytest


@pytest.mark.django_db
class TestAnonymousUrls:
    def test_anonymous_can_access(self, access_tester):
        um = access_tester.url_manager
        for url in um.get_urls("anonymous"):
            for method in um.get_effective_methods(url):
                result = access_tester.test_access(
                    url, "anonymous", method=method, user=None,
                )
                assert result.passed, (
                    f"{url.full_name} [{method}]: {result.reason}"
                )


@pytest.mark.django_db
class TestLoggedInUrls:
    def test_logged_in_can_access(self, access_tester):
        um = access_tester.url_manager
        dp = access_tester.data_provider
        for url in um.get_urls("logged_in"):
            ctx = dp.get_test_context(url, "logged_in")
            for user in ctx.authorized_users:
                for method in um.get_effective_methods(url):
                    result = access_tester.test_access(
                        url, "logged_in", method=method, user=user,
                    )
                    assert result.passed, (
                        f"{url.full_name} [{method}]: {result.reason}"
                    )

    def test_anonymous_cannot_access_logged_in(self, access_tester):
        um = access_tester.url_manager
        for url in um.get_urls("logged_in"):
            for method in um.get_effective_methods(url):
                result = access_tester.test_denial(
                    url, "logged_in", method=method, user=None,
                )
                assert result.passed, (
                    f"{url.full_name} [{method}]: {result.reason}"
                )


@pytest.mark.django_db
class TestCapabilityUrls:
    def test_authorized_can_access(self, access_tester):
        um = access_tester.url_manager
        dp = access_tester.data_provider
        for cap_name in um.config.by_capability:
            for url in um.get_urls("by_capability", cap_name):
                ctx = dp.get_test_context(url, "by_capability", cap_name)
                for user in ctx.authorized_users:
                    for method in um.get_effective_methods(url):
                        result = access_tester.test_access(
                            url, "by_capability", cap_name,
                            method=method, user=user,
                        )
                        assert result.passed, (
                            f"{url.full_name} [{method}] cap={cap_name}: {result.reason}"
                        )

    def test_unauthorized_cannot_access(self, access_tester):
        um = access_tester.url_manager
        dp = access_tester.data_provider
        for cap_name in um.config.by_capability:
            for url in um.get_urls("by_capability", cap_name):
                ctx = dp.get_test_context(url, "by_capability", cap_name)
                for user in ctx.unauthorized_users:
                    for method in um.get_effective_methods(url):
                        result = access_tester.test_denial(
                            url, "by_capability", cap_name,
                            method=method, user=user,
                        )
                        assert result.passed, (
                            f"{url.full_name} [{method}] cap={cap_name}: {result.reason}"
                        )

    def test_anonymous_cannot_access_capability_urls(self, access_tester):
        um = access_tester.url_manager
        for cap_name in um.config.by_capability:
            for url in um.get_urls("by_capability", cap_name):
                for method in um.get_effective_methods(url):
                    result = access_tester.test_denial(
                        url, "by_capability", cap_name,
                        method=method, user=None,
                    )
                    assert result.passed, (
                        f"{url.full_name} [{method}] cap={cap_name}: {result.reason}"
                    )


@pytest.mark.django_db
class TestGroupUrls:
    def test_authorized_can_access(self, access_tester):
        um = access_tester.url_manager
        dp = access_tester.data_provider
        for group_name in um.config.by_group:
            for url in um.get_urls("by_group", group_name):
                ctx = dp.get_test_context(url, "by_group", group_name)
                for user in ctx.authorized_users:
                    for method in um.get_effective_methods(url):
                        result = access_tester.test_access(
                            url, "by_group", group_name,
                            method=method, user=user,
                        )
                        assert result.passed, (
                            f"{url.full_name} [{method}] group={group_name}: {result.reason}"
                        )

    def test_unauthorized_cannot_access(self, access_tester):
        um = access_tester.url_manager
        dp = access_tester.data_provider
        for group_name in um.config.by_group:
            for url in um.get_urls("by_group", group_name):
                ctx = dp.get_test_context(url, "by_group", group_name)
                for user in ctx.unauthorized_users:
                    for method in um.get_effective_methods(url):
                        result = access_tester.test_denial(
                            url, "by_group", group_name,
                            method=method, user=user,
                        )
                        assert result.passed, (
                            f"{url.full_name} [{method}] group={group_name}: {result.reason}"
                        )


@pytest.mark.django_db
class TestUrlCoverage:
    def test_no_missed_urls(self, access_tester):
        um = access_tester.url_manager
        missed = um.get_missed()
        assert len(missed) == 0, (
            f"Found {len(missed)} missed (unconfigured) URLs:\n"
            f"{um.get_missed_report()}"
        )

    def test_parked_urls_warning(self, access_tester):
        um = access_tester.url_manager
        parked = um.get_parked()
        if parked:
            import warnings
            warnings.warn(
                f"{len(parked)} URLs are parked (not tested): "
                f"{[u.full_name for u in parked]}",
                RuntimeWarning,
            )
