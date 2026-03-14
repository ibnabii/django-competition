import pytest
from pydantic import ValidationError

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
    StatsConfig,
)


class TestAccessRule:
    def test_5xx_in_status_codes_rejected(self):
        with pytest.raises(ValidationError):
            AccessRule(status_codes=[500])

    def test_5xx_range_rejected(self):
        with pytest.raises(ValidationError):
            AccessRule(status_codes=[503])

    def test_4xx_allowed(self):
        rule = AccessRule(status_codes=[403, 404])
        assert rule.status_codes == [403, 404]

    def test_302_allowed(self):
        rule = AccessRule(status_codes=[302])
        assert 302 in rule.status_codes

    def test_any_success_default_false(self):
        rule = AccessRule()
        assert rule.any_success is False

    def test_redirect_targets(self):
        rule = AccessRule(
            status_codes=[302],
            allowed_redirect_targets=[RoutePack(names=["account_login"])],
        )
        assert len(rule.allowed_redirect_targets) == 1


class TestRoutePolicy:
    def test_defaults_none(self):
        policy = RoutePolicy(routes=[RoutePack(names=["home"])])
        assert policy.access_rules is None
        assert policy.no_access_rules is None

    def test_explicit_rules(self):
        policy = RoutePolicy(
            routes=[RoutePack(names=["home"])],
            access_rules=[AccessRule(any_success=True)],
        )
        assert policy.access_rules is not None
        assert policy.access_rules[0].any_success is True


class TestDefaultsConfig:
    def test_anonymous_no_no_access_rules(self):
        defaults = DefaultsConfig()
        assert defaults.anonymous.no_access_rules is None

    def test_logged_in_has_defaults(self):
        defaults = DefaultsConfig()
        assert defaults.logged_in.access_rules is not None
        assert len(defaults.logged_in.access_rules) > 0

    def test_anonymous_has_any_success(self):
        defaults = DefaultsConfig()
        assert defaults.anonymous.access_rules[0].any_success is True


class TestMethodStrategy:
    def test_all_values_valid(self):
        for mode in ["ALL_FROM_VIEW", "RESTRICT_TO_CONFIG", "FORCE_CONFIG", "EXTEND_FROM_CONFIG"]:
            mc = MethodConfig(mode=mode)
            assert mc.mode == MethodStrategy(mode)

    def test_default_mode(self):
        mc = MethodConfig()
        assert mc.mode == MethodStrategy.RESTRICT_TO_CONFIG

    def test_default_methods(self):
        mc = MethodConfig()
        assert "GET" in mc.methods
        assert "POST" in mc.methods


class TestStatsConfig:
    def test_defaults(self):
        sc = StatsConfig()
        assert sc.enabled is True
        assert sc.db_path is None
        assert sc.cleanup_on_start is False
        assert sc.soft_response_time_ms == 500


class TestConfig:
    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            Config(
                exclude=ExcludeConfig(),
                unknown_field="value",
            )

    def test_capability_validation(self, settings):
        with pytest.raises(ValidationError):
            Config(
                exclude=ExcludeConfig(),
                capability_class="contest.permissions.capabilities.Capability",
                by_capability={
                    "NONEXISTENT_CAP": [
                        RoutePolicy(routes=[RoutePack(names=["home"])])
                    ]
                },
            )

    def test_valid_capability(self):
        config = Config(
            exclude=ExcludeConfig(),
            capability_class="contest.permissions.capabilities.Capability",
            by_capability={
                "JUDGE_FINALS": [
                    RoutePolicy(routes=[RoutePack(names=["home"])])
                ]
            },
        )
        assert "JUDGE_FINALS" in config.by_capability

    def test_defaults_field(self):
        config = Config(exclude=ExcludeConfig())
        assert isinstance(config.defaults, DefaultsConfig)

    def test_parked_field(self):
        config = Config(
            exclude=ExcludeConfig(),
            parked=[RoutePack(names=["experimental"])],
        )
        assert len(config.parked) == 1


class TestDiscoveredUrl:
    def test_full_name_with_namespace(self):
        url = DiscoveredUrl(
            name="home",
            namespace="contest",
            url_pattern="/contest/",
            view_module="contest.views",
            view_name="HomeView",
            supported_methods=[HttpMethod.GET],
        )
        assert url.full_name == "contest:home"

    def test_full_name_without_namespace(self):
        url = DiscoveredUrl(
            name="home",
            namespace="",
            url_pattern="/",
            view_module="views",
            view_name="HomeView",
            supported_methods=[HttpMethod.GET],
        )
        assert url.full_name == "home"

    def test_has_parameters_true(self):
        url = DiscoveredUrl(
            name="detail",
            namespace="contest",
            url_pattern="/contest/<uuid:pk>/",
            view_module="views",
            view_name="DetailView",
            supported_methods=[HttpMethod.GET],
        )
        assert url.has_parameters is True

    def test_has_parameters_false(self):
        url = DiscoveredUrl(
            name="list",
            namespace="contest",
            url_pattern="/contest/",
            view_module="views",
            view_name="ListView",
            supported_methods=[HttpMethod.GET],
        )
        assert url.has_parameters is False


class TestLoadConfig:
    def test_valid_config_loads(self):
        from contest.tests.urls.utils.load_config import load_config
        config = load_config()
        assert isinstance(config, Config)
        assert config.capability_class is not None
        assert config.exclude is not None
