from dataclasses import dataclass, field
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from contest.tests.urls.access_tester import AccessTester, TestResult
from contest.tests.urls.data_provider import TestContext
from contest.tests.urls.models.config import (
    AccessRule,
    Config,
    DiscoveredUrl,
    ExcludeConfig,
    HttpMethod,
    RoutePolicy,
    RoutePack,
)
from contest.tests.urls.models.url_manager import UrlManager


def make_url(name="home", namespace="", methods=None):
    return DiscoveredUrl(
        name=name,
        namespace=namespace,
        url_pattern=f"/{name}/",
        view_module="views",
        view_name="View",
        supported_methods=methods or [HttpMethod.GET],
    )


def make_manager(access_rules=None, no_access_rules=None):
    policy = RoutePolicy(
        routes=[RoutePack(names=["home"])],
        access_rules=access_rules,
        no_access_rules=no_access_rules,
    )
    config = Config(
        exclude=ExcludeConfig(),
        anonymous=[policy],
    )
    mgr = UrlManager(config=config)
    url = make_url()
    mgr._discovered = [url]
    mgr._url_map = {url.full_name: url}
    mgr.categorize()
    return mgr


def make_mock_response(status_code, path="/", redirect_chain=None):
    response = MagicMock()
    response.status_code = status_code
    response.redirect_chain = redirect_chain or []
    response.request = {"PATH_INFO": path}
    return response


def make_provider(resolved_url="/", method_data=None):
    provider = MagicMock()
    provider.get_test_context.return_value = TestContext(
        resolved_url=resolved_url,
        authorized_users=[],
        unauthorized_users=[],
        method_data=method_data or {},
    )
    return provider


class TestValidation:
    def _make_tester(self, access_rules=None, no_access_rules=None):
        mgr = make_manager(access_rules, no_access_rules)
        client = MagicMock()
        provider = make_provider()
        return AccessTester(mgr, provider, client)

    def test_any_success_passes_200(self):
        tester = self._make_tester()
        rules = [AccessRule(any_success=True)]
        response = make_mock_response(200)
        passed, reason = tester._validate(response, rules, follow=False)
        assert passed

    def test_any_success_passes_301(self):
        tester = self._make_tester()
        rules = [AccessRule(any_success=True)]
        response = make_mock_response(301)
        passed, reason = tester._validate(response, rules, follow=False)
        assert passed

    def test_any_success_fails_403(self):
        tester = self._make_tester()
        rules = [AccessRule(any_success=True)]
        response = make_mock_response(403)
        passed, reason = tester._validate(response, rules, follow=False)
        assert not passed

    def test_status_code_match_passes(self):
        tester = self._make_tester()
        rules = [AccessRule(status_codes=[200])]
        response = make_mock_response(200)
        passed, _ = tester._validate(response, rules, follow=False)
        assert passed

    def test_status_code_mismatch_fails(self):
        tester = self._make_tester()
        rules = [AccessRule(status_codes=[200])]
        response = make_mock_response(403)
        passed, _ = tester._validate(response, rules, follow=False)
        assert not passed

    def test_no_302_means_no_follow(self):
        tester = self._make_tester()
        rules = [AccessRule(status_codes=[200])]
        assert tester._should_follow(rules) is False

    def test_302_means_follow(self):
        tester = self._make_tester()
        rules = [AccessRule(status_codes=[302])]
        assert tester._should_follow(rules) is True

    def test_empty_rules_fails(self):
        tester = self._make_tester()
        response = make_mock_response(200)
        passed, reason = tester._validate(response, [], follow=False)
        assert not passed


class TestRedirectValidation:
    def test_redirect_target_check(self):
        config = Config(exclude=ExcludeConfig())
        mgr = UrlManager(config=config)
        client = MagicMock()
        provider = make_provider()
        tester = AccessTester(mgr, provider, client)

        with patch("contest.tests.urls.access_tester.django_resolve") as mock_resolve:
            mock_result = MagicMock()
            mock_result.namespace = "account"
            mock_result.url_name = "login"
            mock_resolve.return_value = mock_result

            target = RoutePack(names=["login"], name_space="account")
            result = tester._check_redirect_target("/en/accounts/login/", [target])
            assert result is True

    def test_redirect_ignores_query_params(self):
        config = Config(exclude=ExcludeConfig())
        mgr = UrlManager(config=config)
        client = MagicMock()
        provider = make_provider()
        tester = AccessTester(mgr, provider, client)

        with patch("contest.tests.urls.access_tester.django_resolve") as mock_resolve:
            mock_result = MagicMock()
            mock_result.namespace = ""
            mock_result.url_name = "account_login"
            mock_resolve.return_value = mock_result

            target = RoutePack(names=["account_login"])
            result = tester._check_redirect_target("/accounts/login/?next=/foo", [target])
            assert result is True
            # Ensure query params were stripped
            mock_resolve.assert_called_with("/accounts/login/")

    def test_wrong_redirect_target_fails(self):
        config = Config(exclude=ExcludeConfig())
        mgr = UrlManager(config=config)
        client = MagicMock()
        provider = make_provider()
        tester = AccessTester(mgr, provider, client)

        with patch("contest.tests.urls.access_tester.django_resolve") as mock_resolve:
            mock_result = MagicMock()
            mock_result.namespace = ""
            mock_result.url_name = "home"
            mock_resolve.return_value = mock_result

            target = RoutePack(names=["account_login"])
            result = tester._check_redirect_target("/", [target])
            assert result is False


class TestUserSetup:
    def _make_tester(self):
        config = Config(exclude=ExcludeConfig())
        mgr = UrlManager(config=config)
        client = MagicMock()
        provider = make_provider()
        return AccessTester(mgr, provider, client), client

    def test_anonymous_logs_out(self):
        tester, client = self._make_tester()
        user_type = tester._setup_user(None)
        assert user_type == "anonymous"
        client.logout.assert_called_once()

    def test_user_force_login(self):
        tester, client = self._make_tester()
        user = MagicMock()
        user_type = tester._setup_user(user)
        assert user_type == "logged_in"
        client.force_login.assert_called_once_with(user)


class TestRequestExecution:
    def _make_tester(self, rules=None, status_code=200):
        access_rules = rules or [AccessRule(any_success=True)]
        mgr = make_manager(access_rules=access_rules)
        client = MagicMock()
        response = make_mock_response(status_code)
        client.get.return_value = response
        client.post.return_value = response
        provider = make_provider()
        return AccessTester(mgr, provider, client), response

    def test_visit_recorded_on_access(self):
        tester, _ = self._make_tester()
        url = make_url()
        tester.test_access(url, "anonymous", method=HttpMethod.GET, user=None)
        assert len(tester.url_manager._visits) == 1

    def test_visit_recorded_on_denial(self):
        tester, _ = self._make_tester(
            rules=[AccessRule(status_codes=[403])],
            status_code=403,
        )
        mgr = make_manager(no_access_rules=[AccessRule(status_codes=[403])])
        provider = make_provider()
        client = MagicMock()
        response = make_mock_response(403)
        client.get.return_value = response
        tester2 = AccessTester(mgr, provider, client)
        url = make_url()
        tester2.test_denial(url, "anonymous", method=HttpMethod.GET, user=None)
        assert len(tester2.url_manager._visits) == 1

    def test_result_contains_all_fields(self):
        tester, _ = self._make_tester()
        url = make_url()
        result = tester.test_access(url, "anonymous", method=HttpMethod.GET, user=None)
        assert isinstance(result, TestResult)
        assert result.url_full_name == "home"
        assert result.method == "GET"
        assert result.status_code == 200
        assert result.response_time_ms >= 0

    def test_post_data_passed_to_client(self):
        config = Config(exclude=ExcludeConfig())
        mgr = UrlManager(config=config)
        url = make_url("create", methods=[HttpMethod.GET, HttpMethod.POST])
        mgr._discovered = [url]
        mgr._url_map = {url.full_name: url}
        policy = RoutePolicy(
            routes=[RoutePack(names=["create"])],
            access_rules=[AccessRule(any_success=True)],
        )
        mgr._category_map[url.full_name] = ("logged_in", None, policy)
        mgr._category_urls[("logged_in", None)] = [url.full_name]

        client = MagicMock()
        response = make_mock_response(200)
        client.post.return_value = response

        post_data = {"name": "test"}
        provider = make_provider(method_data={"POST": post_data})
        tester = AccessTester(mgr, provider, client)
        tester.test_access(url, "logged_in", method=HttpMethod.POST, user=None)
        client.post.assert_called_once()
        call_kwargs = client.post.call_args[1]
        assert call_kwargs.get("data") == post_data

    def test_no_data_for_get(self):
        config = Config(exclude=ExcludeConfig())
        mgr = UrlManager(config=config)
        url = make_url()
        mgr._discovered = [url]
        mgr._url_map = {url.full_name: url}
        policy = RoutePolicy(
            routes=[RoutePack(names=["home"])],
            access_rules=[AccessRule(any_success=True)],
        )
        mgr._category_map[url.full_name] = ("anonymous", None, policy)
        mgr._category_urls[("anonymous", None)] = [url.full_name]

        client = MagicMock()
        response = make_mock_response(200)
        client.get.return_value = response

        # Provide method_data with GET key (should NOT be passed)
        provider = make_provider(method_data={"GET": {"some": "data"}})
        tester = AccessTester(mgr, provider, client)
        tester.test_access(url, "anonymous", method=HttpMethod.GET, user=None)
        call_kwargs = client.get.call_args[1]
        assert "data" not in call_kwargs or call_kwargs.get("data") is None
