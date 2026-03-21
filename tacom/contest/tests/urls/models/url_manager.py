import warnings
from datetime import datetime, timezone
from statistics import mean, stdev
from types import ModuleType
from typing import Literal

from django.urls import get_resolver, reverse, URLPattern, URLResolver
from pydantic import BaseModel, PrivateAttr

from .config import (
    AccessRule,
    Config,
    DefaultRules,
    DiscoveredUrl,
    HttpMethod,
    MethodStrategy,
    RoutePolicy,
    RoutePack,
    VisitRecord,
)

UrlCategory = Literal[
    "anonymous",
    "logged_in",
    "by_capability",
    "by_group",
    "parked",
    "excluded",
    "missed",
]

_CATEGORY_DEFAULTS_KEY = {
    "anonymous": "anonymous",
    "logged_in": "logged_in",
    "by_capability": "by_capability",
    "by_group": "by_group",
}


class UrlManager(BaseModel):
    config: Config

    _discovered: list[DiscoveredUrl] = PrivateAttr(default_factory=list)
    _excluded: list[DiscoveredUrl] = PrivateAttr(default_factory=list)
    _visits: list[VisitRecord] = PrivateAttr(default_factory=list)
    # (namespace, name) → (category, subcategory, RoutePolicy)
    _category_map: dict[str, tuple[str, str | None, RoutePolicy]] = PrivateAttr(
        default_factory=dict
    )
    # (category, subcategory_or_empty) → list[full_name]
    _category_urls: dict[tuple, list[str]] = PrivateAttr(default_factory=dict)
    # full_name → DiscoveredUrl
    _url_map: dict[str, DiscoveredUrl] = PrivateAttr(default_factory=dict)
    # parked full_names set
    _parked_names: set[str] = PrivateAttr(default_factory=set)

    # ═══════════════════════════════════════
    # 1. URL Discovery
    # ═══════════════════════════════════════

    def discover_urls(self) -> list[DiscoveredUrl]:
        resolver = get_resolver()
        all_urls, excluded = self._walk_patterns(resolver.url_patterns)
        self._discovered = all_urls
        self._excluded = excluded
        self._url_map = {url.full_name: url for url in all_urls}
        return all_urls

    def _walk_patterns(
        self, patterns, prefix="", namespace=""
    ) -> tuple[list[DiscoveredUrl], list[DiscoveredUrl]]:
        results: list[DiscoveredUrl] = []
        excluded: list[DiscoveredUrl] = []

        for pattern in patterns:
            if isinstance(pattern, URLResolver):
                resolver_namespace = pattern.namespace or ""
                resolver_app_name = pattern.app_name or ""

                urlconf = pattern.urlconf_name
                if isinstance(urlconf, ModuleType):
                    module_name = urlconf.__name__
                elif isinstance(urlconf, str):
                    module_name = urlconf
                else:
                    module_name = ""

                if resolver_app_name in self.config.exclude.apps:
                    continue
                if resolver_namespace in self.config.exclude.namespaces:
                    continue
                if module_name in self.config.exclude.modules:
                    continue

                new_namespace = resolver_namespace or namespace
                new_prefix = prefix + str(pattern.pattern)
                sub_results, sub_excluded = self._walk_patterns(
                    pattern.url_patterns, new_prefix, new_namespace
                )
                results.extend(sub_results)
                excluded.extend(sub_excluded)

            elif isinstance(pattern, URLPattern):
                if not pattern.name:
                    continue

                view = self._get_view(pattern.callback)
                view_module = getattr(view, "__module__", "") or ""
                view_name = getattr(view, "__name__", "") or getattr(
                    view, "__qualname__", ""
                )
                methods = self._extract_methods(view)

                url = DiscoveredUrl(
                    name=pattern.name,
                    namespace=namespace,
                    url_pattern=prefix + str(pattern.pattern),
                    view_module=view_module,
                    view_name=view_name,
                    supported_methods=methods if methods else [HttpMethod.GET],
                )

                if self._should_exclude(url):
                    excluded.append(url)
                else:
                    results.append(url)

        return results, excluded

    def _get_view(self, callback):
        if hasattr(callback, "view_class"):
            return callback.view_class
        return callback

    def _extract_methods(self, view) -> list[HttpMethod]:
        methods = []
        for method_name in ("get", "post", "put", "patch", "delete"):
            if hasattr(view, method_name):
                methods.append(HttpMethod(method_name.upper()))
        return methods

    def _should_exclude(self, url: DiscoveredUrl) -> bool:
        if url.name in self.config.exclude.names:
            return True
        if url.namespace in self.config.exclude.namespaces:
            return True
        return False

    # ═══════════════════════════════════════
    # 2. URL Categorization
    # ═══════════════════════════════════════

    def categorize(self) -> None:
        self._category_map = {}
        self._category_urls = {}
        self._parked_names = set()

        # Build parked set
        for route_pack in self.config.parked:
            for name in route_pack.names:
                ns = route_pack.name_space
                full_name = f"{ns}:{name}" if ns else name
                self._parked_names.add(full_name)

        def _register(
            full_name: str, category: str, subcategory: str | None, policy: RoutePolicy
        ):
            self._category_map[full_name] = (category, subcategory, policy)
            key = (category, subcategory)
            if key not in self._category_urls:
                self._category_urls[key] = []
            self._category_urls[key].append(full_name)

        for policy in self.config.anonymous:
            for route_pack in policy.routes:
                for name in route_pack.names:
                    ns = route_pack.name_space
                    full_name = f"{ns}:{name}" if ns else name
                    _register(full_name, "anonymous", None, policy)

        for policy in self.config.logged_in:
            for route_pack in policy.routes:
                for name in route_pack.names:
                    ns = route_pack.name_space
                    full_name = f"{ns}:{name}" if ns else name
                    _register(full_name, "logged_in", None, policy)

        for cap_name, policies in self.config.by_capability.items():
            for policy in policies:
                for route_pack in policy.routes:
                    for name in route_pack.names:
                        ns = route_pack.name_space
                        full_name = f"{ns}:{name}" if ns else name
                        _register(full_name, "by_capability", cap_name, policy)

        for group_name, policies in self.config.by_group.items():
            for policy in policies:
                for route_pack in policy.routes:
                    for name in route_pack.names:
                        ns = route_pack.name_space
                        full_name = f"{ns}:{name}" if ns else name
                        _register(full_name, "by_group", group_name, policy)

    def get_urls(
        self,
        category: UrlCategory,
        subcategory: str | None = None,
    ) -> list[DiscoveredUrl]:
        if category == "parked":
            return self.get_parked()
        if category == "missed":
            return self.get_missed()
        if category == "excluded":
            return self._excluded

        key = (category, subcategory)
        full_names = self._category_urls.get(key, [])
        result = []
        for fn in full_names:
            url = self._url_map.get(fn)
            if url:
                result.append(url)
        return result

    def get_policy(
        self,
        url: DiscoveredUrl,
        category: UrlCategory,
        subcategory: str | None = None,
    ) -> RoutePolicy:
        entry = self._category_map.get(url.full_name)
        if entry:
            _, _, policy = entry
        else:
            # Return a default policy
            policy = RoutePolicy(routes=[])

        defaults_key = _CATEGORY_DEFAULTS_KEY.get(category, "logged_in")
        default_rules: DefaultRules = getattr(self.config.defaults, defaults_key)

        resolved_access = (
            policy.access_rules
            if policy.access_rules is not None
            else default_rules.access_rules
        )

        # anonymous never gets no_access_rules
        if category == "anonymous":
            resolved_no_access = None
        else:
            resolved_no_access = (
                policy.no_access_rules
                if policy.no_access_rules is not None
                else default_rules.no_access_rules
            )

        return RoutePolicy(
            routes=policy.routes,
            access_rules=resolved_access,
            no_access_rules=resolved_no_access,
        )

    def get_effective_methods(self, url: DiscoveredUrl) -> list[HttpMethod]:
        mode = self.config.method_strategy.mode
        config_methods = [
            HttpMethod(m.upper()) for m in self.config.method_strategy.methods
        ]
        view_methods = url.supported_methods

        if mode == MethodStrategy.ALL_FROM_VIEW:
            return view_methods
        elif mode == MethodStrategy.RESTRICT_TO_CONFIG:
            return [m for m in view_methods if m in config_methods]
        elif mode == MethodStrategy.FORCE_CONFIG:
            return config_methods
        elif mode == MethodStrategy.EXTEND_FROM_CONFIG:
            combined = list(view_methods)
            for m in config_methods:
                if m not in combined:
                    combined.append(m)
            return combined
        return view_methods

    # ═══════════════════════════════════════
    # 3. Missed / Parked URL Detection
    # ═══════════════════════════════════════

    def get_missed(self) -> list[DiscoveredUrl]:
        missed = []
        for url in self._discovered:
            fn = url.full_name
            if fn not in self._category_map and fn not in self._parked_names:
                missed.append(url)
        return missed

    def get_missed_count(self) -> int:
        return len(self.get_missed())

    def get_missed_report(self) -> str:
        missed = self.get_missed()
        if not missed:
            return "No missed URLs."
        else:
            by_module = {}
            for url in missed:
                by_module.setdefault(url.view_module, []).append(url)

            lines = [f"Missed URLs ({len(missed)} total):"]
            for module, urls in sorted(by_module.items()):
                lines.append(f"\n  Module: {module}")
                for url in sorted(urls, key=lambda u: (u.namespace or "", u.name)):
                    ns_part = f"{url.namespace}:" if url.namespace else ""
                    lines.append(f"    {ns_part}{url.name:<40} {url.view_name}")
        return "\n".join(lines)

    def get_parked(self) -> list[DiscoveredUrl]:
        result = []
        for url in self._discovered:
            if url.full_name in self._parked_names:
                result.append(url)
        return result

    def get_parked_count(self) -> int:
        return len(self.get_parked())

    # ═══════════════════════════════════════
    # 4. URL Resolution Helper
    # ═══════════════════════════════════════

    def resolve_url(self, full_name: str, kwargs: dict | None = None) -> str:
        if ":" in full_name:
            namespace, name = full_name.split(":", 1)
            return reverse(full_name, kwargs=kwargs or {})
        return reverse(full_name, kwargs=kwargs or {})

    # ═══════════════════════════════════════
    # 5. Summary / Validation
    # ═══════════════════════════════════════

    def get_summary(self) -> dict:
        by_cap = {
            cap: len(self._category_urls.get(("by_capability", cap), []))
            for cap in self.config.by_capability
        }
        by_group = {
            grp: len(self._category_urls.get(("by_group", grp), []))
            for grp in self.config.by_group
        }
        return {
            "total_discovered": len(self._discovered),
            "excluded": len(self._excluded),
            "anonymous": len(self._category_urls.get(("anonymous", None), [])),
            "logged_in": len(self._category_urls.get(("logged_in", None), [])),
            "by_capability": by_cap,
            "by_group": by_group,
            "parked": len(self._parked_names),
            "missed": self.get_missed_count(),
        }

    def validate_config(self) -> list[str]:
        issues = []
        seen: dict[str, list[str]] = {}

        def _scan(policies, category, subcategory=None):
            for policy in policies:
                for rp in policy.routes:
                    for name in rp.names:
                        ns = rp.name_space
                        fn = f"{ns}:{name}" if ns else name
                        label = f"{category}/{subcategory}" if subcategory else category
                        seen.setdefault(fn, []).append(label)

        _scan(self.config.anonymous, "anonymous")
        _scan(self.config.logged_in, "logged_in")
        for cap, policies in self.config.by_capability.items():
            _scan(policies, "by_capability", cap)
        for grp, policies in self.config.by_group.items():
            _scan(policies, "by_group", grp)

        for fn, labels in seen.items():
            if len(labels) > 1:
                issues.append(f"WARNING: {fn} appears in multiple groups: {labels}")

        for cat_name in ("anonymous", "logged_in"):
            policies = getattr(self.config, cat_name)
            if not policies:
                issues.append(f"INFO: {cat_name} group is empty")

        if self.config.capability_class:
            module_path, class_name = self.config.capability_class.rsplit(".", 1)
            try:
                import importlib

                mod = importlib.import_module(module_path)
                cap_class = getattr(mod, class_name)
                allowed = {c.name for c in cap_class}
                unknown = set(self.config.by_capability.keys()) - allowed
                if unknown:
                    issues.append(f"ERROR: Unknown capabilities in config: {unknown}")
            except Exception as e:
                issues.append(f"ERROR: Could not load capability_class: {e}")

        return issues

    # ═══════════════════════════════════════
    # 6. Statistics / Visit Tracking
    # ═══════════════════════════════════════

    def record_visit(self, visit: VisitRecord) -> None:
        self._visits.append(visit)
        threshold = self.config.stats.soft_response_time_ms
        if threshold > 0 and visit.response_time_ms > threshold:
            warnings.warn(
                f"Slow response: {visit.url_full_name} [{visit.method}] "
                f"{visit.response_time_ms:.1f}ms > {threshold}ms threshold",
                RuntimeWarning,
                stacklevel=2,
            )

    def persist_run(self, run_label: str | None = None) -> None:
        if not self.config.stats.enabled:
            return
        from .db import UrlManagerDb

        db = UrlManagerDb(config=self.config)
        db.persist_run(
            url_manager=self,
            run_label=run_label,
        )

    def get_stats_summary(self) -> dict:
        if not self._visits:
            return {
                "total_visits": 0,
                "avg_response_time_ms": 0.0,
                "max_response_time_ms": 0.0,
                "min_response_time_ms": 0.0,
                "slowest_urls": [],
                "outliers": [],
                "inconsistent": [],
                "warnings": [],
            }

        times = [v.response_time_ms for v in self._visits]
        global_mean = mean(times)
        global_std = stdev(times) if len(times) > 1 else 0.0

        # Per-URL aggregation
        url_times: dict[str, list[float]] = {}
        for v in self._visits:
            key = f"{v.url_full_name}[{v.method}]"
            url_times.setdefault(key, []).append(v.response_time_ms)

        url_avgs = {k: mean(v) for k, v in url_times.items()}
        slowest = sorted(url_avgs.items(), key=lambda x: x[1], reverse=True)[:10]

        outliers = []
        for url_key, avg_ms in url_avgs.items():
            if avg_ms > global_mean + global_std:
                outliers.append(
                    {
                        "url": url_key,
                        "avg_ms": avg_ms,
                        "global_mean": global_mean,
                        "std_dev": global_std,
                    }
                )

        inconsistent = []
        for url_key, times_list in url_times.items():
            if len(times_list) > 1:
                url_std = stdev(times_list)
                if url_std > global_std:
                    inconsistent.append(
                        {
                            "url": url_key,
                            "min_ms": min(times_list),
                            "max_ms": max(times_list),
                            "std_dev": url_std,
                        }
                    )

        threshold = self.config.stats.soft_response_time_ms
        warn_list = []
        if threshold > 0:
            for v in self._visits:
                if v.response_time_ms > threshold:
                    warn_list.append(
                        {
                            "url": v.url_full_name,
                            "method": v.method,
                            "time_ms": v.response_time_ms,
                            "threshold": threshold,
                        }
                    )

        return {
            "total_visits": len(self._visits),
            "avg_response_time_ms": global_mean,
            "max_response_time_ms": max(times),
            "min_response_time_ms": min(times),
            "slowest_urls": [{"url": k, "avg_ms": v} for k, v in slowest],
            "outliers": outliers,
            "inconsistent": inconsistent,
            "warnings": warn_list,
        }
