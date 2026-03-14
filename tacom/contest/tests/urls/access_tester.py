import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from django.test import Client
from django.urls import resolve as django_resolve

from .models.config import AccessRule, HttpMethod, RoutePack, VisitRecord
from .models.url_manager import UrlCategory, UrlManager


@dataclass
class TestResult:
    __test__ = False  # prevent pytest from collecting this as a test class
    passed: bool
    url_full_name: str
    method: str
    user_type: str
    expected_access: bool
    status_code: int
    response_time_ms: float
    reason: str
    followed_redirects: bool
    redirect_chain: list[str] = field(default_factory=list)
    final_url: str | None = None


class AccessTester:
    def __init__(
        self,
        url_manager: UrlManager,
        data_provider,
        client: Client,
    ):
        self.url_manager = url_manager
        self.data_provider = data_provider
        self.client = client

    # ═══════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════

    def test_access(
        self,
        url,
        category: UrlCategory,
        subcategory: str | None = None,
        user=None,
        method: HttpMethod = HttpMethod.GET,
    ) -> TestResult:
        policy = self.url_manager.get_policy(url, category, subcategory)
        ctx = self.data_provider.get_test_context(url, category, subcategory)
        rules = policy.access_rules or []
        return self._execute(
            ctx.resolved_url, method, user, rules,
            expected_access=True, url=url,
            category=category, subcategory=subcategory, ctx=ctx,
        )

    def test_denial(
        self,
        url,
        category: UrlCategory,
        subcategory: str | None = None,
        user=None,
        method: HttpMethod = HttpMethod.GET,
    ) -> TestResult:
        policy = self.url_manager.get_policy(url, category, subcategory)
        ctx = self.data_provider.get_test_context(url, category, subcategory)
        rules = policy.no_access_rules or []
        return self._execute(
            ctx.resolved_url, method, user, rules,
            expected_access=False, url=url,
            category=category, subcategory=subcategory, ctx=ctx,
        )

    # ═══════════════════════════════════════
    # Overridable Hooks
    # ═══════════════════════════════════════

    def _make_request(
        self,
        resolved_url: str,
        method: HttpMethod,
        follow: bool,
        data: dict | None = None,
    ):
        client_method = getattr(self.client, method.value.lower())
        if data:
            return client_method(resolved_url, data=data, follow=follow)
        return client_method(resolved_url, follow=follow)

    def _setup_user(self, user) -> str:
        if user is None:
            self.client.logout()
            return "anonymous"
        self.client.force_login(user)
        return "logged_in"

    def _validate(
        self,
        response,
        rules: list[AccessRule],
        follow: bool,
    ) -> tuple[bool, str]:
        if not rules:
            return False, "No rules defined"

        status = response.status_code

        for rule in rules:
            if rule.any_success:
                if status < 400:
                    return True, f"Success: {status} (any_success=True)"
                continue

            if not follow:
                if status in rule.status_codes:
                    return True, f"Status {status} matches expected {rule.status_codes}"
                continue

            # Followed redirects
            if status < 400 and rule.allowed_redirect_targets:
                final_url = response.request.get("PATH_INFO", "")
                if self._check_redirect_target(final_url, rule.allowed_redirect_targets):
                    return True, f"Redirect to {final_url} matches allowed targets"
                return False, f"Redirect to {final_url} not in allowed targets {[t.names for t in rule.allowed_redirect_targets]}"

            if status in rule.status_codes:
                return True, f"Status {status} matches expected {rule.status_codes}"

        return False, f"Status {status} did not match any rule (rules: {rules})"

    def _check_redirect_target(
        self,
        final_url: str,
        allowed_targets: list[RoutePack],
    ) -> bool:
        path = final_url.split("?")[0]
        try:
            resolved = django_resolve(path)
        except Exception:
            return False

        for target in allowed_targets:
            ns = target.name_space
            if resolved.namespace == ns or (not ns and not resolved.namespace):
                if resolved.url_name in target.names:
                    return True
        return False

    # ═══════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════

    def _execute(
        self, resolved_url, method, user, rules,
        expected_access, url, category, subcategory, ctx,
    ) -> TestResult:
        user_type = self._setup_user(user)
        follow = self._should_follow(rules)
        _write_methods = {HttpMethod.POST, HttpMethod.PUT, HttpMethod.PATCH}
        request_data = (
            ctx.method_data.get(method.value)
            if ctx and method in _write_methods
            else None
        )

        start = time.perf_counter()
        response = self._make_request(resolved_url, method, follow, data=request_data)
        elapsed_ms = (time.perf_counter() - start) * 1000

        passed, reason = self._validate(response, rules, follow)

        redirect_chain = [u for u, _ in getattr(response, "redirect_chain", [])]
        final_url = response.request.get("PATH_INFO") if follow else None

        result = TestResult(
            passed=passed,
            url_full_name=url.full_name,
            method=method.value,
            user_type=user_type,
            expected_access=expected_access,
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
            reason=reason,
            followed_redirects=follow,
            redirect_chain=redirect_chain,
            final_url=final_url,
        )

        self.url_manager.record_visit(VisitRecord(
            url_full_name=url.full_name,
            method=method,
            user_type=user_type,
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
            followed_redirects=follow,
            redirect_chain=redirect_chain,
            timestamp=datetime.now(timezone.utc),
        ))

        return result

    def _should_follow(self, rules: list[AccessRule]) -> bool:
        for rule in rules:
            if 302 in rule.status_codes:
                return True
        return False
