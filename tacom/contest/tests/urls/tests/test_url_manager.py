import pytest

from contest.tests.urls.models.config import (
    AccessRule,
    Config,
    DefaultRules,
    DefaultsConfig,
    DiscoveredUrl,
    ExcludeConfig,
    HttpMethod,
    MethodConfig,
    MethodStrategy,
    RoutePolicy,
    RoutePack,
)
from contest.tests.urls.models.url_manager import UrlManager


def make_url(name: str, namespace: str = "", methods=None) -> DiscoveredUrl:
    return DiscoveredUrl(
        name=name,
        namespace=namespace,
        url_pattern=f"/{name}/",
        view_module="test.views",
        view_name="TestView",
        supported_methods=methods or [HttpMethod.GET],
    )


def make_manager(
    anonymous=None,
    logged_in=None,
    by_capability=None,
    by_group=None,
    parked=None,
    method_mode=MethodStrategy.RESTRICT_TO_CONFIG,
    method_list=None,
    exclude=None,
) -> UrlManager:
    config = Config(
        exclude=exclude or ExcludeConfig(),
        capability_class="contest.permissions.capabilities.Capability",
        anonymous=anonymous or [],
        logged_in=logged_in or [],
        by_capability=by_capability or {},
        by_group=by_group or {},
        parked=parked or [],
        method_strategy=MethodConfig(
            mode=method_mode,
            methods=method_list or ["GET", "POST"],
        ),
    )
    return UrlManager(config=config)


class TestDiscovery:
    @pytest.mark.django_db
    def test_discover_finds_urls(self):
        mgr = make_manager()
        urls = mgr.discover_urls()
        assert len(urls) > 0

    @pytest.mark.django_db
    def test_discover_extracts_namespace(self):
        mgr = make_manager()
        urls = mgr.discover_urls()
        namespaced = [u for u in urls if u.namespace == "contest"]
        assert len(namespaced) > 0

    @pytest.mark.django_db
    def test_exclude_by_app(self):
        mgr = make_manager(exclude=ExcludeConfig(apps=["admin"]))
        urls = mgr.discover_urls()
        admin_urls = [u for u in urls if "admin" in u.view_module]
        assert len(admin_urls) == 0

    @pytest.mark.django_db
    def test_exclude_by_name(self):
        mgr = make_manager(exclude=ExcludeConfig(names=["home"]))
        urls = mgr.discover_urls()
        home_urls = [u for u in urls if u.name == "home"]
        assert len(home_urls) == 0

    @pytest.mark.django_db
    def test_url_map_populated(self):
        mgr = make_manager()
        mgr.discover_urls()
        assert len(mgr._url_map) > 0


class TestCategorization:
    def _mgr_with_urls(self) -> tuple[UrlManager, list[DiscoveredUrl]]:
        url_anon = make_url("home")
        url_login = make_url("profile", "contest")
        url_cap = make_url("judging_finals_list", "contest")

        mgr = make_manager(
            anonymous=[RoutePolicy(routes=[RoutePack(names=["home"])])],
            logged_in=[RoutePolicy(routes=[RoutePack(names=["profile"], name_space="contest")])],
            by_capability={
                "JUDGE_FINALS": [RoutePolicy(routes=[RoutePack(names=["judging_finals_list"], name_space="contest")])]
            },
        )
        mgr._discovered = [url_anon, url_login, url_cap]
        mgr._url_map = {u.full_name: u for u in [url_anon, url_login, url_cap]}
        mgr.categorize()
        return mgr, [url_anon, url_login, url_cap]

    def test_categorize_anonymous(self):
        mgr, urls = self._mgr_with_urls()
        anon_urls = mgr.get_urls("anonymous")
        assert any(u.name == "home" for u in anon_urls)

    def test_categorize_logged_in(self):
        mgr, urls = self._mgr_with_urls()
        li_urls = mgr.get_urls("logged_in")
        assert any(u.name == "profile" for u in li_urls)

    def test_categorize_by_capability(self):
        mgr, urls = self._mgr_with_urls()
        cap_urls = mgr.get_urls("by_capability", "JUDGE_FINALS")
        assert any(u.name == "judging_finals_list" for u in cap_urls)

    def test_missed_urls(self):
        mgr, urls = self._mgr_with_urls()
        # Add an extra URL not in any config group
        extra = make_url("unconfigured", "contest")
        mgr._discovered.append(extra)
        mgr._url_map[extra.full_name] = extra
        mgr.categorize()
        missed = mgr.get_missed()
        assert any(u.name == "unconfigured" for u in missed)

    def test_parked_urls(self):
        url = make_url("parked_url")
        mgr = make_manager(
            parked=[RoutePack(names=["parked_url"])],
        )
        mgr._discovered = [url]
        mgr._url_map = {url.full_name: url}
        mgr.categorize()
        parked = mgr.get_parked()
        assert any(u.name == "parked_url" for u in parked)
        missed = mgr.get_missed()
        assert not any(u.name == "parked_url" for u in missed)

    def test_url_in_multiple_groups_warning(self):
        mgr = make_manager(
            anonymous=[RoutePolicy(routes=[RoutePack(names=["home"])])],
            logged_in=[RoutePolicy(routes=[RoutePack(names=["home"])])],
        )
        url = make_url("home")
        mgr._discovered = [url]
        mgr._url_map = {url.full_name: url}
        mgr.categorize()
        issues = mgr.validate_config()
        assert any("multiple groups" in issue for issue in issues)


class TestPolicyResolution:
    def _mgr_with_policy(self, policy_kwargs=None) -> tuple[UrlManager, DiscoveredUrl]:
        url = make_url("profile", "contest")
        policy = RoutePolicy(
            routes=[RoutePack(names=["profile"], name_space="contest")],
            **(policy_kwargs or {}),
        )
        mgr = make_manager(logged_in=[policy])
        mgr._discovered = [url]
        mgr._url_map = {url.full_name: url}
        mgr.categorize()
        return mgr, url

    def test_get_policy_with_defaults(self):
        mgr, url = self._mgr_with_policy()
        policy = mgr.get_policy(url, "logged_in")
        # Should use defaults.logged_in.access_rules
        assert policy.access_rules is not None
        assert len(policy.access_rules) > 0

    def test_get_policy_with_override(self):
        mgr, url = self._mgr_with_policy({
            "access_rules": [AccessRule(status_codes=[200])],
        })
        policy = mgr.get_policy(url, "logged_in")
        assert policy.access_rules[0].status_codes == [200]

    def test_anonymous_never_has_no_access_rules(self):
        url = make_url("home")
        policy_cfg = RoutePolicy(
            routes=[RoutePack(names=["home"])],
            no_access_rules=[AccessRule(status_codes=[403])],
        )
        mgr = make_manager(anonymous=[policy_cfg])
        mgr._discovered = [url]
        mgr._url_map = {url.full_name: url}
        mgr.categorize()
        policy = mgr.get_policy(url, "anonymous")
        assert policy.no_access_rules is None


class TestMethodStrategy:
    def _make_url_with_methods(self, methods):
        return make_url("view", "contest", methods)

    def test_all_from_view(self):
        mgr = make_manager(method_mode=MethodStrategy.ALL_FROM_VIEW)
        url = self._make_url_with_methods([HttpMethod.GET, HttpMethod.POST, HttpMethod.DELETE])
        result = mgr.get_effective_methods(url)
        assert set(result) == {HttpMethod.GET, HttpMethod.POST, HttpMethod.DELETE}

    def test_restrict_to_config(self):
        mgr = make_manager(
            method_mode=MethodStrategy.RESTRICT_TO_CONFIG,
            method_list=["GET", "POST"],
        )
        url = self._make_url_with_methods([HttpMethod.GET, HttpMethod.POST, HttpMethod.DELETE])
        result = mgr.get_effective_methods(url)
        assert set(result) == {HttpMethod.GET, HttpMethod.POST}

    def test_force_config(self):
        mgr = make_manager(
            method_mode=MethodStrategy.FORCE_CONFIG,
            method_list=["GET", "POST"],
        )
        url = self._make_url_with_methods([HttpMethod.GET])
        result = mgr.get_effective_methods(url)
        assert HttpMethod.POST in result

    def test_extend_from_config(self):
        mgr = make_manager(
            method_mode=MethodStrategy.EXTEND_FROM_CONFIG,
            method_list=["GET", "POST"],
        )
        url = self._make_url_with_methods([HttpMethod.GET, HttpMethod.DELETE])
        result = mgr.get_effective_methods(url)
        assert set(result) == {HttpMethod.GET, HttpMethod.POST, HttpMethod.DELETE}


class TestStats:
    def test_record_visit(self):
        from datetime import timezone
        from contest.tests.urls.models.config import VisitRecord
        from datetime import datetime

        mgr = make_manager()
        visit = VisitRecord(
            url_full_name="contest:home",
            method=HttpMethod.GET,
            user_type="anonymous",
            status_code=200,
            response_time_ms=42.0,
            followed_redirects=False,
            timestamp=datetime.now(timezone.utc),
        )
        mgr.record_visit(visit)
        assert len(mgr._visits) == 1

    def test_soft_threshold_warning(self):
        from datetime import timezone, datetime
        from contest.tests.urls.models.config import VisitRecord, StatsConfig

        config = Config(
            exclude=ExcludeConfig(),
            stats=StatsConfig(soft_response_time_ms=100),
        )
        mgr = UrlManager(config=config)
        visit = VisitRecord(
            url_full_name="contest:home",
            method=HttpMethod.GET,
            user_type="anonymous",
            status_code=200,
            response_time_ms=200.0,
            followed_redirects=False,
            timestamp=datetime.now(timezone.utc),
        )
        with pytest.warns(RuntimeWarning, match="Slow response"):
            mgr.record_visit(visit)

    def test_get_stats_summary_empty(self):
        mgr = make_manager()
        summary = mgr.get_stats_summary()
        assert summary["total_visits"] == 0

    def test_get_summary(self):
        mgr = make_manager(
            anonymous=[RoutePolicy(routes=[RoutePack(names=["home"])])],
        )
        url = make_url("home")
        mgr._discovered = [url]
        mgr._url_map = {url.full_name: url}
        mgr.categorize()
        summary = mgr.get_summary()
        assert summary["anonymous"] == 1
        assert summary["missed"] == 0
