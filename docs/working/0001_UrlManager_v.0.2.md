# UrlManager v0.2 Specification

**Version:** 0.2  
**Date:** 2026-03-14  
**Status:** Draft for Review  
**Previous:** v0.1 (reviewed, comments incorporated)

---

## 1. Executive Summary

UrlManager is a **data registry and URL catalogue** for automated access control testing of Django URLs. It does **not** execute tests itself -- it discovers, categorizes, and serves URL metadata and access policies to standard pytest test cases.

**Key Goals:**
- Zero-configuration URL discovery from Django's resolver
- Declarative access control policies via YAML configuration
- Automatic detection of unconfigured ("missed") URLs
- Pluggable data provider for project-specific test setup (users, objects, URL resolution)
- Portable: the `tests/urls` module is self-contained and copiable to other Django projects
- SQLite-based run tracking for statistics and historical comparison

**What UrlManager Does:**
- Discovers all Django URLs and extracts metadata (namespace, name, pattern, HTTP methods)
- Categorizes URLs into groups: `anonymous`, `logged_in`, `by_capability`, `by_group`, `parked`, `excluded`, `missed`
- Provides access policies (access_rules, no_access_rules) with defaults inheritance
- Accepts visit feedback (timing, status codes) for statistics
- Persists run data to SQLite for cross-run comparison

**What UrlManager Does NOT Do:**
- Does not execute HTTP requests (tests do this via `django.test.Client`)
- Does not create test users or objects (the pluggable data provider does this)
- Does not run assertions (pytest test cases do this)

---

## 2. Architecture Overview

### 2.1 Component Structure

```
tacom/contest/tests/urls/
├── models/
│   ├── __init__.py
│   ├── config.py           # Pydantic configuration models (existing, enhanced)
│   ├── url_manager.py      # Core UrlManager class (existing, redesigned)
│   └── db.py               # SQLite database model for run tracking (NEW)
├── utils/
│   ├── __init__.py
│   ├── load_config.py      # YAML config loader (existing)
│   └── get_url_manager.py  # Factory function (existing, enhanced)
├── access_tester.py        # Base AccessTester + TestResult (NEW)
├── data_provider.py        # Abstract data provider + project-specific implementation (NEW)
├── config.yaml             # Main configuration file (existing, enhanced)
├── conftest.py             # Pytest fixtures wiring everything together (NEW)
├── docs/                   # Module documentation (NEW)
│   ├── 0001_UrlManager_v.1.0.md   # Approved specification (placed here after approval)
│   ├── examples_basic.md          # Basic usage example
│   ├── examples_override.md       # AccessTester override example
│   └── examples_fixtures.md       # Fixture setup example
└── tests/                  # Framework self-tests (NEW)
    ├── __init__.py
    ├── test_url_manager.py         # Unit tests for UrlManager
    ├── test_access_tester.py       # Unit tests for AccessTester
    ├── test_config.py              # Unit tests for Config models
    └── test_db.py                  # Unit tests for SQLite tracking
```

### 2.2 Data Flow

```
Django URL Resolver
        ↓
[UrlManager.discover_urls()] → list[DiscoveredUrl] with metadata (name, namespace, pattern, methods)
        ↓
[UrlManager.categorize()] → URLs grouped by access requirements using config
        ↓
[UrlManager.get_missed()] → URLs not in any config group (should be zero)
        ↓
Tests read URL groups from UrlManager
        ↓
Tests call DataProvider to get: resolved URL, authorized users, unauthorized users
        ↓
Tests execute HTTP requests via django.test.Client
        ↓
Tests call UrlManager.record_visit() with timing/status data
        ↓
[UrlManager.persist_run()] → SQLite database for historical tracking
```

### 2.3 Role Separation

| Component | Responsibility |
|-----------|---------------|
| **UrlManager** | URL discovery, categorization, policy lookup, statistics collection, run persistence |
| **Config (YAML + Pydantic)** | Declarative access policies, defaults, exclusions, method strategy |
| **AccessTester** | Full test cycle: HTTP requests via django.test.Client, response validation against policies, automatic stats recording. Inheritable for project-specific overrides |
| **DataProvider** | Project-specific: resolve URL patterns to real paths, create test users with appropriate permissions |
| **Pytest tests** | Iterate URL groups, orchestrate AccessTester calls, assert on TestResult |
| **SQLite DB** | Persist run metadata, per-URL category snapshots, visit statistics |

### 2.4 Current State Analysis

- ✅ `Config`, `RoutePack`, `RoutePolicy`, `AccessRule` Pydantic models -- well-designed foundation
- ✅ YAML loader with validation
- ✅ `list_urls` management command -- inspiration for URL traversal (but UrlManager has its own)
- ✅ Existing factories: `ContestFactory`, `UserFactory`, `EntryFactory`, `CategoryFactory`, `StyleFactory`
- ⚠️ `UrlManager` model exists but is minimal (will be redesigned)
- ❌ No URL categorization logic
- ❌ No data provider
- ❌ No statistics / run tracking

---

## 3. Configuration Schema Design

### 3.1 YAML Structure

```yaml
# ── Exclusions ──────────────────────────────────────────────
exclude:
  apps:
    - "admin"
    - "debug_toolbar"
  modules:
    - "django.conf.urls.i18n"
  names:
    - "account_logout"
  namespaces:
    - "rosetta"

# ── Capability class (dynamic import path) ──────────────────
capability_class: "contest.permissions.capabilities.Capability"

# ── Data provider class (dynamic import path) ───────────────
data_provider_class: "contest.tests.urls.data_provider.ContestDataProvider"

# ── Method testing strategy ─────────────────────────────────
method_strategy:
  mode: "RESTRICT_TO_CONFIG"     # ALL_FROM_VIEW | RESTRICT_TO_CONFIG | FORCE_CONFIG | EXTEND_FROM_CONFIG
  methods: ["GET", "POST"]       # used by RESTRICT_TO_CONFIG, FORCE_CONFIG, EXTEND_FROM_CONFIG

# ── Statistics / DB settings ────────────────────────────────
stats:
  enabled: true
  db_path: null                  # null = same directory as config.yaml; string = override path
  cleanup_on_start: false        # true = truncate DB before run; false = append new run
  soft_response_time_ms: 500     # warn if any request exceeds this (0 = disabled)

# ── Group-level defaults ────────────────────────────────────
# Applied when a RoutePolicy does NOT specify access_rules or no_access_rules.
# Explicit values in RoutePolicy REPLACE (not extend) defaults.
defaults:
  anonymous:
    access_rules:
      - any_success: true
    # NOTE: anonymous has NO no_access_rules (never tested for denial)

  logged_in:
    access_rules:
      - any_success: true
    no_access_rules:
      - status_codes: [302]
        allowed_redirect_targets:
          - names: ["account_login"]

  by_capability:
    access_rules:
      - any_success: true
    no_access_rules:
      - status_codes: [302]
        allowed_redirect_targets:
          - names: ["account_login"]

  by_group:
    access_rules:
      - any_success: true
    no_access_rules:
      - status_codes: [403]

# ── URL Groups ──────────────────────────────────────────────

anonymous:
  - routes:
      - names: ["home", "about", "contact"]
  - routes:
      - namespace: "account"
        names: ["login", "signup"]
    access_rules:
      - any_success: true

logged_in:
  - routes:
      - namespace: "contest"
        names: ["entry_create", "entry_list"]
    # Uses defaults.logged_in (not specified → inherited)
  - routes:
      - namespace: "contest"
        names: ["profile_edit"]
    no_access_rules:    # Override default: expect hard 403 instead of redirect
      - status_codes: [403]

by_capability:
  JUDGE_FINALS:
    - routes:
        - namespace: "contest"
          names: ["judging_finals_list", "judging_finals_detail"]
      # Uses defaults.by_capability

    - routes:
        - namespace: "contest"
          names: ["judging_finals_category"]
      no_access_rules:  # Override: redirect to contest detail instead of login
        - status_codes: [302]
          allowed_redirect_targets:
            - namespace: "contest"
              names: ["contest_detail"]

  VIEW_SCORESHEET:
    - routes:
        - namespace: "contest"
          names: ["scoresheet_view"]

by_group:
  staff:
    - routes:
        - namespace: "contest"
          names: ["admin_dashboard"]

# ── Parked URLs (explicitly deferred, WARNING only) ─────────
parked:
  - namespace: "contest"
    names: ["experimental_feature"]
```

### 3.2 Defaults Inheritance Rules

When a `RoutePolicy` is defined:
- If `access_rules` is **not specified** → use `defaults.{category}.access_rules`
- If `no_access_rules` is **not specified** → use `defaults.{category}.no_access_rules`
- If either **is specified** → use the policy value (full replacement, not merge)
- `anonymous` category: `no_access_rules` is **never applied**, even if accidentally set in defaults

### 3.3 Redirect Logic (driven by `status_codes`)

The presence of `302` in `status_codes` determines redirect behavior:

**No 302 in `status_codes`:**
- Request is made with `follow=False`
- Response status code is checked directly against `status_codes`
- If `any_success=True`, any `response.status_code < 400` passes

**302 in `status_codes`:**
- Request is made with `follow=True`
- The **final** response must be successful (`response.status_code < 400`)
- The final URL is resolved to `namespace:name` and matched against `allowed_redirect_targets`
- Query parameters are **ignored** during redirect target matching
- The full redirect chain is tracked for debugging but only the final destination is validated

**Hard rule:** `500` (or any 5xx) is **never valid** in `no_access_rules.status_codes`. Config validation will reject it.

---

## 4. Pydantic Models

### 4.1 Configuration Models (enhanced `config.py`)

```python
from enum import Enum
from pydantic import BaseModel, field_validator


class ExcludeConfig(BaseModel):
    apps: list[str] = []
    names: list[str] = []
    modules: list[str] = []
    namespaces: list[str] = []


class RoutePack(BaseModel):
    names: list[str]
    name_space: str = ""


class AccessRule(BaseModel):
    any_success: bool = False
    status_codes: list[int] = []
    allowed_redirect_targets: list[RoutePack] = []

    @field_validator("status_codes")
    @classmethod
    def no_5xx_codes(cls, v):
        for code in v:
            if 500 <= code < 600:
                raise ValueError(f"5xx status codes are not valid in access rules: {code}")
        return v


class RoutePolicy(BaseModel):
    routes: list[RoutePack]
    access_rules: list[AccessRule] | None = None      # None = use defaults
    no_access_rules: list[AccessRule] | None = None    # None = use defaults


class DefaultRules(BaseModel):
    access_rules: list[AccessRule] = [AccessRule(any_success=True)]
    no_access_rules: list[AccessRule] | None = None    # None for anonymous


class DefaultsConfig(BaseModel):
    anonymous: DefaultRules = DefaultRules(
        access_rules=[AccessRule(any_success=True)],
        no_access_rules=None,
    )
    logged_in: DefaultRules = DefaultRules()
    by_capability: DefaultRules = DefaultRules()
    by_group: DefaultRules = DefaultRules()


class MethodStrategy(str, Enum):
    ALL_FROM_VIEW = "ALL_FROM_VIEW"
    RESTRICT_TO_CONFIG = "RESTRICT_TO_CONFIG"
    FORCE_CONFIG = "FORCE_CONFIG"
    EXTEND_FROM_CONFIG = "EXTEND_FROM_CONFIG"


class MethodConfig(BaseModel):
    mode: MethodStrategy = MethodStrategy.RESTRICT_TO_CONFIG
    methods: list[str] = ["GET", "POST"]


class StatsConfig(BaseModel):
    enabled: bool = True
    db_path: str | None = None       # None = co-located with config.yaml
    cleanup_on_start: bool = False   # False = append; True = truncate before run
    soft_response_time_ms: int = 500 # 0 = disabled


class Config(BaseModel):
    class Config:
        extra = "forbid"
        str_strip_whitespace = True

    exclude: ExcludeConfig
    capability_class: str | None = None
    data_provider_class: str | None = None

    anonymous: list[RoutePolicy] = []
    logged_in: list[RoutePolicy] = []
    by_capability: dict[str, list[RoutePolicy]] = {}
    by_group: dict[str, list[RoutePolicy]] = {}
    parked: list[RoutePack] = []

    defaults: DefaultsConfig = DefaultsConfig()
    method_strategy: MethodConfig = MethodConfig()
    stats: StatsConfig = StatsConfig()

    @field_validator("by_capability", mode="before")
    @classmethod
    def validate_by_capability(cls, v, info):
        # ... existing validator (unchanged)
        ...
```

### 4.2 DiscoveredUrl Model

```python
from enum import Enum
from pydantic import BaseModel


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class DiscoveredUrl(BaseModel):
    """A URL discovered from Django's URL resolver."""
    name: str                           # URL name (e.g., "entry_detail")
    namespace: str = ""                 # URL namespace (e.g., "contest")
    url_pattern: str                    # Django pattern (e.g., "contest/<slug:contest_slug>/entry/<int:pk>/")
    view_module: str                    # View module path (e.g., "contest.views.views")
    view_name: str                      # View class/function name (e.g., "EntryDetailView")
    supported_methods: list[HttpMethod] # HTTP methods the view actually handles

    @property
    def full_name(self) -> str:
        """Returns namespace:name format."""
        return f"{self.namespace}:{self.name}" if self.namespace else self.name

    @property
    def has_parameters(self) -> bool:
        """Whether the URL pattern contains parameters like <int:pk>."""
        return "<" in self.url_pattern
```

### 4.3 Visit Record (for statistics)

```python
from datetime import datetime

class VisitRecord(BaseModel):
    """Feedback from a test about a URL visit."""
    url_full_name: str               # namespace:name
    method: HttpMethod
    user_type: str                   # "anonymous", "logged_in", "capability:{name}", "group:{name}"
    status_code: int
    response_time_ms: float
    followed_redirects: bool
    redirect_chain: list[str] = []   # tracked for debugging
    timestamp: datetime
```

---

## 5. UrlManager API Design

```python
from typing import Literal
from pydantic import BaseModel

UrlCategory = Literal[
    "anonymous", "logged_in", "by_capability", "by_group",
    "parked", "excluded", "missed"
]


class UrlManager(BaseModel):
    config: Config
    _discovered: list[DiscoveredUrl] = []
    _visits: list[VisitRecord] = []

    # ═══════════════════════════════════════
    # 1. URL Discovery
    # ═══════════════════════════════════════

    def discover_urls(self) -> list[DiscoveredUrl]:
        """
        Traverse Django's URL resolver, extract all URLPatterns.
        Populates internal _discovered list.
        Applies exclusion rules from config.exclude.
        Returns the full list (excluding excluded ones).
        """
        ...

    def _walk_patterns(self, patterns, prefix="", namespace="") -> list[DiscoveredUrl]:
        """Recursively walk URL patterns (self-contained, no management command dependency)."""
        ...

    def _extract_methods(self, view) -> list[HttpMethod]:
        """
        Extract actually handled HTTP methods from a view.
        For CBVs: inspect which of get/post/put/patch/delete are
        actually implemented (not just inherited from base View).
        For FBVs: check decorators or default to [GET].
        """
        ...

    def _should_exclude(self, url: DiscoveredUrl) -> bool:
        """Check against config.exclude (apps, modules, names, namespaces)."""
        ...

    # ═══════════════════════════════════════
    # 2. URL Categorization
    # ═══════════════════════════════════════

    def categorize(self) -> None:
        """
        Categorize all discovered URLs against config groups.
        Must be called after discover_urls().
        Internally builds lookup dicts for fast access.
        """
        ...

    def get_urls(
        self,
        category: UrlCategory,
        subcategory: str | None = None,
    ) -> list[DiscoveredUrl]:
        """
        Get URLs for a given category.
        For by_capability/by_group, subcategory is the capability/group name.
        """
        ...

    def get_policy(
        self,
        url: DiscoveredUrl,
        category: UrlCategory,
        subcategory: str | None = None,
    ) -> RoutePolicy:
        """
        Get the RoutePolicy for a URL in a given category.
        Applies defaults inheritance:
        - If policy.access_rules is None → defaults.{category}.access_rules
        - If policy.no_access_rules is None → defaults.{category}.no_access_rules
        Returns a "resolved" policy with no None fields.
        """
        ...

    def get_effective_methods(self, url: DiscoveredUrl) -> list[HttpMethod]:
        """
        Apply method_strategy to determine which methods to test for a URL.
        
        ALL_FROM_VIEW:        return url.supported_methods
        RESTRICT_TO_CONFIG:   return intersection(url.supported_methods, config.methods)
        FORCE_CONFIG:         return config.methods
        EXTEND_FROM_CONFIG:   return union(url.supported_methods, config.methods)
        """
        ...

    # ═══════════════════════════════════════
    # 3. Missed / Parked URL Detection
    # ═══════════════════════════════════════

    def get_missed(self) -> list[DiscoveredUrl]:
        """
        URLs discovered by crawler but not in ANY config group
        (not in anonymous, logged_in, by_capability, by_group, parked, or excluded).
        These should be zero for a well-configured project.
        """
        ...

    def get_missed_count(self) -> int:
        """Shorthand for len(get_missed())."""
        ...

    def get_missed_report(self) -> str:
        """
        Human-readable report of missed URLs, grouped by:
        - module (view_module)
        - namespace
        - name
        - actual pattern
        """
        ...

    def get_parked(self) -> list[DiscoveredUrl]:
        """URLs explicitly listed in config.parked (deferred, warning only)."""
        ...

    def get_parked_count(self) -> int:
        ...

    # ═══════════════════════════════════════
    # 4. URL Resolution Helper
    # ═══════════════════════════════════════

    def resolve_url(self, full_name: str, kwargs: dict | None = None) -> str:
        """
        Resolve namespace:name to an actual path using django.urls.reverse().
        Convenience wrapper for tests.
        """
        ...

    # ═══════════════════════════════════════
    # 5. Summary / Validation
    # ═══════════════════════════════════════

    def get_summary(self) -> dict:
        """
        Returns:
            {
                "total_discovered": 150,
                "excluded": 15,
                "anonymous": 10,
                "logged_in": 40,
                "by_capability": {"JUDGE_FINALS": 5, "VIEW_SCORESHEET": 3, ...},
                "by_group": {"staff": 2},
                "parked": 3,
                "missed": 0,
            }
        """
        ...

    def validate_config(self) -> list[str]:
        """
        Validate configuration for issues:
        - URL in multiple groups (warning)
        - 5xx codes in no_access_rules (error, also caught by Pydantic)
        - Empty groups (info)
        - Capabilities not matching capability_class (error, existing)
        Returns list of warning/error messages.
        """
        ...

    # ═══════════════════════════════════════
    # 6. Statistics / Visit Tracking
    # ═══════════════════════════════════════

    def record_visit(self, visit: VisitRecord) -> None:
        """
        Record a URL visit from a test.
        Appends to in-memory list.
        Checks soft_response_time_ms threshold (emits warning if exceeded).
        """
        ...

    def persist_run(self, run_label: str | None = None) -> None:
        """
        Persist current run data to SQLite:
        - Run metadata (timestamp, label, totals)
        - Category snapshot (which URLs are in each category for this run)
        - All visit records
        
        Uses config.stats.db_path (default: same dir as config.yaml).
        If config.stats.cleanup_on_start: truncates DB before writing.
        """
        ...

    def get_stats_summary(self) -> dict:
        """
        In-memory aggregate stats for current run:
        - total_visits, avg_response_time_ms
        - slowest URLs (top 10)
        - outliers: URLs with avg > 1 std deviation from mean
        - inconsistent: URLs with high response time variance
        """
        ...
```

---

## 6. Data Provider Interface

### 6.1 Abstract Contract

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from django.contrib.auth.models import AbstractUser


@dataclass
class TestContext:
    """Returned by DataProvider for a given URL + category."""
    resolved_url: str                        # Real, callable URL path (e.g., "/contest/my-contest/judging/finals/")
    authorized_users: list[AbstractUser]     # Users expected to access successfully
    unauthorized_users: list[AbstractUser]   # Users expected to be denied


class BaseDataProvider(ABC):
    """
    Abstract data provider that tests/urls module depends on.
    Project-specific implementations handle object creation and user setup.
    Referenced in config via data_provider_class.
    """

    @abstractmethod
    def setup(self) -> None:
        """
        One-time setup: create shared objects (contests, categories, etc.).
        Called once before test session.
        """
        ...

    @abstractmethod
    def get_test_context(
        self,
        url: DiscoveredUrl,
        category: UrlCategory,
        subcategory: str | None = None,
    ) -> TestContext:
        """
        For a given URL and its category, return:
        1. A resolved (real, callable) URL with actual object IDs
        2. List of users who SHOULD be able to access it
        3. List of users who should NOT be able to access it

        The provider knows project-specific rules, e.g.:
        - Capabilities are per-contest: creates 2 contests,
          grants capability for contest A, tests both contest A URL (authorized)
          and contest B URL (unauthorized, same user with capability for wrong contest)
        - Groups are native Django: creates users in/out of groups
        - Anonymous: returns no authorized users (anonymous = no user),
          and returns logged-in users as "unauthorized" (for negative testing: N/A for anonymous)
        """
        ...

    @abstractmethod
    def get_anonymous_user(self) -> None:
        """
        Returns None (anonymous = no user to log in).
        Exists for API symmetry.
        """
        return None

    @abstractmethod
    def teardown(self) -> None:
        """Cleanup if needed."""
        ...
```

### 6.2 Project-Specific Implementation (example for this project)

```python
class ContestDataProvider(BaseDataProvider):
    """
    Knows that:
    - Capabilities are scoped to (user, contest) pairs
    - URLs with <slug:contest_slug> need a real Contest object
    - For by_capability tests: create 2 contests (A and B)
      - Authorized: user with capability for contest A, URL for contest A
      - Unauthorized: same user but URL for contest B (has capability for wrong contest),
        plus user without capability, plus anonymous
    """

    def setup(self):
        self.contest_a = ContestFactory(slug="test-contest-a")
        self.contest_b = ContestFactory(slug="test-contest-b")
        self.anonymous_user = None
        self.basic_user = UserFactory()  # logged in, no capabilities
        # ... create styles, categories as needed for URL resolution

    def get_test_context(self, url, category, subcategory=None):
        kwargs = self._resolve_url_params(url)
        resolved_url = reverse(url.full_name, kwargs=kwargs)

        if category == "anonymous":
            return TestContext(
                resolved_url=resolved_url,
                authorized_users=[],  # anonymous = no user
                unauthorized_users=[], # no denial tests for anonymous
            )

        if category == "logged_in":
            return TestContext(
                resolved_url=resolved_url,
                authorized_users=[self.basic_user],
                unauthorized_users=[],  # anonymous tested separately
            )

        if category == "by_capability":
            cap_user = self._create_user_with_capability(subcategory, self.contest_a)
            wrong_contest_user = self._create_user_with_capability(subcategory, self.contest_b)
            return TestContext(
                resolved_url=resolved_url,  # URL for contest_a
                authorized_users=[cap_user],
                unauthorized_users=[self.basic_user, wrong_contest_user],
            )

        if category == "by_group":
            group_user = self._create_user_in_group(subcategory)
            return TestContext(
                resolved_url=resolved_url,
                authorized_users=[group_user],
                unauthorized_users=[self.basic_user],
            )

    def _resolve_url_params(self, url: DiscoveredUrl) -> dict:
        """
        Parse url_pattern for parameters and resolve them to real objects.
        E.g., <slug:contest_slug> → {"contest_slug": "test-contest-a"}
        """
        ...

    def _create_user_with_capability(self, capability_name, contest):
        """Create user + grant capability for specific contest."""
        ...

    def _create_user_in_group(self, group_name):
        """Create user + add to Django group."""
        ...
```

### 6.3 Design Rationale

The DataProvider is the **only project-specific code** in the testing framework. Everything else (UrlManager, Config, DB tracking) is generic and portable. When copying the `tests/urls` module to another project, one only needs to:

1. Write a new `DataProvider` implementation
2. Update `data_provider_class` in `config.yaml`
3. Update URL group assignments in `config.yaml`

Complex ownership tests (e.g., "user owns Entry which belongs to Category which belongs to Contest, and Entry is handled by Package") are **outside** this framework's scope for v0.2. Those require dedicated functional tests. The DataProvider handles the common cases: capabilities, groups, login-required.

---

## 7. AccessTester Class Design

### 7.1 TestResult Model

```python
from dataclasses import dataclass


@dataclass
class TestResult:
    """Result of a single access test."""
    passed: bool
    url_full_name: str
    method: str
    user_type: str              # "anonymous", "logged_in", "capability:{name}", "group:{name}"
    expected_access: bool       # True = testing access, False = testing denial
    status_code: int
    response_time_ms: float
    reason: str                 # Human-readable explanation of pass/fail
    followed_redirects: bool
    redirect_chain: list[str]   # Full chain for debugging
    final_url: str | None       # Final URL after redirects (if followed)
```

### 7.2 Base AccessTester

```python
import time
from datetime import datetime, timezone
from django.test import Client
from django.urls import resolve as django_resolve


class AccessTester:
    """
    Executes the full test cycle: HTTP request → validation → stats recording.
    Sits between UrlManager (data) and pytest tests (orchestration).
    Inheritable for project-specific overrides.
    """

    def __init__(
        self,
        url_manager: UrlManager,
        data_provider: BaseDataProvider,
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
        url: DiscoveredUrl,
        category: UrlCategory,
        subcategory: str | None = None,
        user=None,
        method: HttpMethod = HttpMethod.GET,
    ) -> TestResult:
        """
        Test that a user CAN access a URL.
        Validates response against access_rules from the resolved policy.
        Automatically records visit stats.

        Args:
            url: The discovered URL to test
            category: URL category (anonymous, logged_in, etc.)
            subcategory: Capability name or group name
            user: User to log in (None = anonymous)
            method: HTTP method to use
        """
        policy = self.url_manager.get_policy(url, category, subcategory)
        ctx = self.data_provider.get_test_context(url, category, subcategory)
        rules = policy.access_rules  # already resolved with defaults
        return self._execute(ctx.resolved_url, method, user, rules,
                             expected_access=True, url=url, category=category,
                             subcategory=subcategory)

    def test_denial(
        self,
        url: DiscoveredUrl,
        category: UrlCategory,
        subcategory: str | None = None,
        user=None,
        method: HttpMethod = HttpMethod.GET,
    ) -> TestResult:
        """
        Test that a user CANNOT access a URL.
        Validates response against no_access_rules from the resolved policy.
        Automatically records visit stats.
        """
        policy = self.url_manager.get_policy(url, category, subcategory)
        ctx = self.data_provider.get_test_context(url, category, subcategory)
        rules = policy.no_access_rules  # already resolved with defaults
        return self._execute(ctx.resolved_url, method, user, rules,
                             expected_access=False, url=url, category=category,
                             subcategory=subcategory)

    # ═══════════════════════════════════════
    # Overridable Hooks
    # ═══════════════════════════════════════

    def _make_request(
        self,
        resolved_url: str,
        method: HttpMethod,
        follow: bool,
    ):
        """
        Execute HTTP request. Override to add custom headers, middleware setup, etc.
        Returns Django test response.
        """
        client_method = getattr(self.client, method.value.lower())
        return client_method(resolved_url, follow=follow)

    def _setup_user(self, user) -> str:
        """
        Prepare client for user. Override for custom auth setup.
        Returns user_type string for stats.
        """
        if user is None:
            self.client.logout()
            return "anonymous"
        self.client.force_login(user)
        return "logged_in"  # subclass refines to "capability:{name}" etc.

    def _validate(
        self,
        response,
        rules: list[AccessRule],
        follow: bool,
    ) -> tuple[bool, str]:
        """
        Core validation logic. Override for custom validation.

        Returns (passed, reason) tuple.
        """
        status = response.status_code

        for rule in rules:
            if rule.any_success:
                if status < 400:
                    return True, f"Success: {status} (any_success=True)"
                continue

            if not follow:
                # Direct status check (no redirects followed)
                if status in rule.status_codes:
                    return True, f"Status {status} matches expected {rule.status_codes}"
                continue

            # Followed redirects: validate final destination
            if status < 400 and rule.allowed_redirect_targets:
                final_url = response.request["PATH_INFO"]
                if self._check_redirect_target(final_url, rule.allowed_redirect_targets):
                    return True, f"Redirect to {final_url} matches allowed targets"
                return False, f"Redirect to {final_url} not in allowed targets"

            if status in rule.status_codes:
                return True, f"Status {status} matches expected {rule.status_codes}"

        return False, f"Status {status} did not match any rule"

    def _check_redirect_target(
        self,
        final_url: str,
        allowed_targets: list[RoutePack],
    ) -> bool:
        """
        Check if the final redirect URL matches allowed targets.
        Query parameters are IGNORED.
        """
        # Strip query params
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
        expected_access, url, category, subcategory,
    ) -> TestResult:
        """Orchestrates: setup user → determine follow → request → validate → record."""
        user_type = self._setup_user(user)
        follow = self._should_follow(rules)

        start = time.perf_counter()
        response = self._make_request(resolved_url, method, follow)
        elapsed_ms = (time.perf_counter() - start) * 1000

        passed, reason = self._validate(response, rules, follow)

        redirect_chain = [url for url, _ in getattr(response, "redirect_chain", [])]
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

        # Auto-record stats
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
        """Determine if redirects should be followed based on 302 in status_codes."""
        for rule in rules:
            if 302 in rule.status_codes:
                return True
        return False
```

### 7.3 Project-Specific Override Example

```python
class ContestAccessTester(AccessTester):
    """
    Project-specific overrides for the contest app.
    Refines user_type reporting for capability/group users.
    Can override behavior for ownership-based URLs.
    """

    def _setup_user(self, user) -> str:
        """Refine user_type to include capability/group info."""
        if user is None:
            self.client.logout()
            return "anonymous"
        self.client.force_login(user)
        # If user has capability info attached by DataProvider:
        if hasattr(user, "_test_capability"):
            return f"capability:{user._test_capability}"
        if hasattr(user, "_test_group"):
            return f"group:{user._test_group}"
        return "logged_in"

    def _make_request(self, resolved_url, method, follow):
        """Could add custom headers for HTMX detection, etc."""
        return super()._make_request(resolved_url, method, follow)
```

### 7.4 Fixture Wiring (`conftest.py`)

```python
import pytest
from django.test import Client

from .models.url_manager import UrlManager
from .utils.load_config import load_config
from .data_provider import ContestDataProvider
from .access_tester import AccessTester  # or ContestAccessTester


@pytest.fixture(scope="session")
def url_config():
    return load_config()


@pytest.fixture(scope="session")
def url_manager(url_config):
    mgr = UrlManager(config=url_config)
    mgr.discover_urls()
    mgr.categorize()
    return mgr


@pytest.fixture(scope="session")
def data_provider(url_manager):
    provider = ContestDataProvider()
    provider.setup()
    yield provider
    provider.teardown()


@pytest.fixture
def access_tester(url_manager, data_provider, client):
    """
    Per-test fixture: fresh Client for each test, shared UrlManager and DataProvider.
    Tests only need this single fixture.
    """
    return AccessTester(
        url_manager=url_manager,
        data_provider=data_provider,
        client=client,
    )


def pytest_sessionfinish(session, exitstatus):
    """Persist run stats after all tests complete."""
    # Access url_manager from session fixture and persist
    # (implementation detail: session-scoped fixture teardown)
    ...
```

---

## 8. HTTP Method Discovery & Testing Modes

### 8.1 Method Extraction from Views

UrlManager extracts **actually handled** methods from views, not just declared ones:

```python
def _extract_methods(self, view) -> list[HttpMethod]:
    """
    For CBVs: check which of (get, post, put, patch, delete) are
    actually defined on the view class itself (not inherited from
    base django.views.generic.View).

    E.g. UpdateView actually implements get() and post().
         DeleteView implements get() and post() (confirmation + action).
         ListView implements only get().

    For FBVs: default to [GET] unless decorated with require_http_methods.
    """
```

### 8.2 Four Testing Modes (global config)

| Mode | Behavior | Example: View has [GET, POST, DELETE], config has [GET, POST] |
|------|----------|--------------------------------------------------------------|
| `ALL_FROM_VIEW` | Test every method the view handles | Test: GET, POST, DELETE |
| `RESTRICT_TO_CONFIG` | Intersection of view methods and config list | Test: GET, POST |
| `FORCE_CONFIG` | Force config methods regardless of view | Test: GET, POST |
| `EXTEND_FROM_CONFIG` | Union of config list and view methods | Test: GET, POST, DELETE |

| Mode | Example: View has [GET] only, config has [GET, POST] |
|------|------------------------------------------------------|
| `ALL_FROM_VIEW` | Test: GET |
| `RESTRICT_TO_CONFIG` | Test: GET |
| `FORCE_CONFIG` | Test: GET, POST |
| `EXTEND_FROM_CONFIG` | Test: GET, POST |

**Future consideration:** Automatic 405 Method Not Allowed testing for methods NOT handled by the view could be added in a later version.

---

## 9. SQLite Database Model (`models/db.py`)

### 9.1 Location & Lifecycle

- **Default path:** Same directory as `config.yaml` (e.g., `tacom/contest/tests/urls/urlmanager_runs.db`)
- **Override:** Set `stats.db_path` in YAML to any absolute or relative path
- **Cleanup mode:** `stats.cleanup_on_start: true` truncates all tables before a new run
- **Append mode (default):** `stats.cleanup_on_start: false` keeps all historical runs

### 9.2 Schema

```sql
-- Test run metadata
CREATE TABLE IF NOT EXISTS test_run (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    label       TEXT,                   -- optional human label (e.g., "nightly-build-42")
    started_at  TEXT NOT NULL,          -- ISO 8601 timestamp
    finished_at TEXT,                   -- set when persist_run() completes
    total_discovered  INTEGER,
    total_excluded    INTEGER,
    total_anonymous   INTEGER,
    total_logged_in   INTEGER,
    total_by_capability INTEGER,
    total_by_group    INTEGER,
    total_parked      INTEGER,
    total_missed      INTEGER,
    total_visits      INTEGER,
    avg_response_ms   REAL
);

-- Snapshot of URL categorization for each run
CREATE TABLE IF NOT EXISTS run_url_category (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER NOT NULL REFERENCES test_run(id),
    full_name   TEXT NOT NULL,          -- namespace:name
    url_pattern TEXT NOT NULL,
    view_module TEXT NOT NULL,
    view_name   TEXT NOT NULL,
    category    TEXT NOT NULL,          -- anonymous, logged_in, by_capability, by_group, parked, missed, excluded
    subcategory TEXT,                   -- capability name or group name (NULL for others)
    methods     TEXT NOT NULL           -- comma-separated: "GET,POST"
);

-- Individual visit records
CREATE TABLE IF NOT EXISTS visit (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL REFERENCES test_run(id),
    url_full_name   TEXT NOT NULL,
    method          TEXT NOT NULL,
    user_type       TEXT NOT NULL,      -- anonymous, logged_in, capability:{name}, group:{name}
    status_code     INTEGER NOT NULL,
    response_time_ms REAL NOT NULL,
    followed_redirects INTEGER NOT NULL, -- 0 or 1
    redirect_chain  TEXT,               -- JSON array of URLs
    timestamp       TEXT NOT NULL        -- ISO 8601
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_run_url_category_run ON run_url_category(run_id);
CREATE INDEX IF NOT EXISTS idx_run_url_category_cat ON run_url_category(category);
CREATE INDEX IF NOT EXISTS idx_visit_run ON visit(run_id);
CREATE INDEX IF NOT EXISTS idx_visit_url ON visit(url_full_name);
```

### 9.3 Usage Scenarios

**Compare missed URLs across runs:**
```sql
SELECT r.id, r.started_at, r.total_missed,
       GROUP_CONCAT(c.full_name, ', ') as missed_urls
FROM test_run r
JOIN run_url_category c ON c.run_id = r.id AND c.category = 'missed'
GROUP BY r.id
ORDER BY r.started_at DESC
LIMIT 10;
```

**Track response time trends:**
```sql
SELECT v.url_full_name, r.started_at,
       AVG(v.response_time_ms) as avg_ms
FROM visit v
JOIN test_run r ON r.id = v.run_id
GROUP BY v.url_full_name, r.id
ORDER BY v.url_full_name, r.started_at;
```

**Identify run where a URL moved from missed to configured:**
```sql
SELECT r1.started_at as was_missed, r2.started_at as was_configured,
       c1.full_name
FROM run_url_category c1
JOIN test_run r1 ON r1.id = c1.run_id
JOIN run_url_category c2 ON c2.full_name = c1.full_name
JOIN test_run r2 ON r2.id = c2.run_id
WHERE c1.category = 'missed' AND c2.category != 'missed'
  AND r2.started_at > r1.started_at;
```

---

## 10. Access Control Test Scenarios

### 10.1 Positive Testing (Can Access)

For each URL in a category, test that the **authorized** user type CAN access:

| Category | Who Is Tested | What DataProvider Returns | Expected Outcome |
|----------|---------------|--------------------------|------------------|
| `anonymous` | No user (anonymous request) | `authorized_users=[]` | Matches `access_rules` |
| `logged_in` | Logged-in user (basic) | `authorized_users=[basic_user]` | Matches `access_rules` |
| `by_capability/{cap}` | User with capability for correct contest | `authorized_users=[cap_user]` | Matches `access_rules` |
| `by_group/{group}` | User in the group | `authorized_users=[group_user]` | Matches `access_rules` |

### 10.2 Negative Testing (Cannot Access)

For URLs that restrict access, test that **unauthorized** user types are denied:

| Category | Who Is Denied | What DataProvider Returns | Expected Outcome |
|----------|---------------|--------------------------|------------------|
| `anonymous` | **N/A** -- anonymous pages are not tested for denial | — | — |
| `logged_in` | Anonymous user | `unauthorized_users=[]` (test uses anonymous directly) | Matches `no_access_rules` |
| `by_capability/{cap}` | Basic user (no cap), user with cap for wrong contest | `unauthorized_users=[basic_user, wrong_contest_user]` | Matches `no_access_rules` |
| `by_group/{group}` | Basic user (not in group) | `unauthorized_users=[basic_user]` | Matches `no_access_rules` |

### 10.3 Expanded Test Matrix for `by_capability` URL

For URL: `contest:judging_finals_list` (requires `JUDGE_FINALS` capability)

| User | Expected | Rule Source |
|------|----------|-------------|
| Anonymous | Denied: 302 → login | `no_access_rules` (default or per-group for anonymous denial from logged_in defaults) |
| Logged-in (no cap) | Denied: 302 → login or 403 | `no_access_rules` |
| User with JUDGE_FINALS for **contest A** | Allowed: 200 | `access_rules` |
| User with JUDGE_FINALS for **contest B** (wrong contest) | Denied | `no_access_rules` |
| User with OTHER_CAPABILITY for contest A | Denied | `no_access_rules` |

### 10.4 How Tests Work with AccessTester

Tests become clean orchestrators. AccessTester handles HTTP calls, validation, and stats recording automatically.

```python
@pytest.mark.django_db
class TestAnonymousUrls:
    def test_anonymous_can_access(self, access_tester):
        """Anonymous users can access all URLs in the anonymous group."""
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
        """Logged-in users can access all URLs in the logged_in group."""
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
        """Anonymous users are denied access to logged_in URLs."""
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
        """Users with the correct capability can access capability-gated URLs."""
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
        """Users without the capability (or with wrong-contest capability) are denied."""
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
        """Anonymous users are denied access to capability-gated URLs."""
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
```

---

## 11. Statistics & Reporting

### 11.1 In-Memory Metrics (current run)

```python
def get_stats_summary(self) -> dict:
    """
    Returns:
        {
            "total_visits": 450,
            "avg_response_time_ms": 47.2,
            "max_response_time_ms": 523.0,
            "min_response_time_ms": 12.0,
            "slowest_urls": [
                {"url": "contest:judging_finals", "method": "GET", "avg_ms": 523.0},
                ...
            ],
            "outliers": [
                # URLs with avg response time > 1 std deviation from the global mean
                {"url": "contest:entry_create", "avg_ms": 312.0, "global_mean": 47.2, "std_dev": 65.1},
            ],
            "inconsistent": [
                # URLs with high variance in response times (suggests N^2 or data-dependent perf)
                {"url": "contest:entry_list", "min_ms": 20.0, "max_ms": 890.0, "std_dev": 340.0},
            ],
            "warnings": [
                # Visits exceeding soft_response_time_ms threshold
                {"url": "contest:entry_list", "method": "GET", "time_ms": 890.0, "threshold": 500},
            ],
        }
    """
```

### 11.2 Parallel Test Worker Compatibility

Since `pytest-xdist` runs workers in separate processes:
- SQLite is accessed via file locking (SQLite handles concurrent writes natively for small workloads)
- Each worker writes to the same DB file with the same `run_id`
- `persist_run()` is called in a `conftest.py` session-scoped fixture teardown
- In-memory stats are per-worker; the DB provides the aggregated view post-run

### 11.3 Reporting Output

Stats are persisted to SQLite. Console output is minimal (driven by tests via `warnings.warn` and `pytest.fail`). Post-run analysis is done via SQL queries against the DB.

---

## 12. Implementation Roadmap

### Phase 1: Core Models & Discovery
1. Enhance `config.py` with new Pydantic models (`DefaultsConfig`, `MethodConfig`, `StatsConfig`, etc.)
2. Redesign `UrlManager` with discovery and categorization
3. Implement `_walk_patterns()`, `_extract_methods()`, `_should_exclude()`
4. Implement `categorize()`, `get_urls()`, `get_policy()` with defaults inheritance
5. Implement `get_missed()`, `get_parked()`, `get_missed_report()`
6. Write unit tests for Config models and UrlManager (see Section 13)

### Phase 2: AccessTester
1. Create `TestResult` dataclass
2. Create base `AccessTester` with `test_access()`, `test_denial()`, `_validate()`, `_make_request()`
3. Implement redirect validation with query param stripping
4. Implement `_should_follow()` logic (302 in status_codes)
5. Create `ContestAccessTester` project-specific override
6. Write unit tests for AccessTester (see Section 13)

### Phase 3: Data Provider
1. Create `BaseDataProvider` abstract class
2. Create `ContestDataProvider` project-specific implementation
3. Write tests verifying provider produces valid test contexts

### Phase 4: SQLite Tracking
1. Create `models/db.py` with schema creation and CRUD
2. Implement `record_visit()`, `persist_run()`, `get_stats_summary()`
3. Handle DB path resolution, cleanup mode
4. Write tests for DB operations (see Section 13)

### Phase 5: Pytest Integration
1. Create `conftest.py` fixtures (`url_manager`, `data_provider`, `access_tester`)
2. Write generic test classes (anonymous, logged_in, by_capability, by_group, coverage)
3. Wire session teardown for `persist_run()`

### Phase 6: Documentation
1. Create `docs/` folder inside `tests/urls`
2. Write `examples_basic.md` -- basic usage with sample config
3. Write `examples_override.md` -- AccessTester override example
4. Write `examples_fixtures.md` -- fixture setup example
5. Place approved specification as `0001_UrlManager_v.1.0.md`

---

## 13. Documentation Plan

All documentation lives in `tacom/contest/tests/urls/docs/`.

### 13.1 `examples_basic.md` -- Basic Usage

A complete, ready-to-use example covering:

1. **Minimal `config.yaml`** with 2-3 anonymous URLs, 2-3 logged_in URLs, 1 capability group
2. **DataProvider implementation** using `ContestFactory` and `UserFactory` from `contest.factories`
3. **Test file** with all test classes (anonymous, logged_in, capability, coverage) using `access_tester` fixture
4. **conftest.py** showing fixture wiring

The example should be copy-paste-ready: a developer reading it can set up URL testing for their project in minutes.

```markdown
# Example outline (in examples_basic.md):

## Step 1: Create config.yaml
(minimal YAML with exclude, anonymous, logged_in, one capability)

## Step 2: Implement DataProvider
(class using ContestFactory, UserFactory with get_test_context for each category)

## Step 3: Set up conftest.py
(url_manager, data_provider, access_tester fixtures)

## Step 4: Write tests
(TestAnonymousUrls, TestLoggedInUrls, TestCapabilityUrls, TestUrlCoverage)

## Step 5: Run
pytest tacom/contest/tests/urls/ -v
```

### 13.2 `examples_override.md` -- AccessTester Override

Example showing:

1. **Custom `ContestAccessTester`** that overrides `_setup_user()` to tag capability/group info
2. **Override `_make_request()`** to add custom headers (e.g., simulating HTMX requests)
3. **Override `test_access()`** for ownership-based URLs that need special handling
4. **Updated conftest.py** using the custom tester instead of base

```python
# Example: overriding for ownership URLs
class ContestAccessTester(AccessTester):
    OWNERSHIP_URLS = {"contest:package_detail", "contest:package_list"}

    def test_access(self, url, category, subcategory=None, user=None, method=HttpMethod.GET):
        if url.full_name in self.OWNERSHIP_URLS:
            return self._test_ownership_access(url, user, method)
        return super().test_access(url, category, subcategory, user, method)

    def _test_ownership_access(self, url, user, method):
        # Custom logic: create Entry → Category → Contest → Package chain
        # Resolve URL with real package_id
        # Test with owner (pass) and non-owner (fail)
        ...
```

### 13.3 `examples_fixtures.md` -- Fixture Setup Deep Dive

Detailed guide on:

1. **Session-scoped vs function-scoped fixtures** -- why `url_manager` and `data_provider` are session-scoped, `access_tester` is function-scoped (fresh Client per test)
2. **Fixture dependency chain**: `url_config` → `url_manager` → `data_provider` → `access_tester`
3. **xdist compatibility** -- how fixtures work with parallel workers
4. **Session teardown** for `persist_run()` -- ensuring stats are saved even if tests fail
5. **Custom fixture for specific test modules** -- e.g., a test file that only tests capability URLs

```python
# Example: scoped fixture with teardown
@pytest.fixture(scope="session")
def url_manager(url_config):
    mgr = UrlManager(config=url_config)
    mgr.discover_urls()
    mgr.categorize()
    yield mgr
    mgr.persist_run(run_label="pytest-session")

# Example: per-test access_tester with fresh client
@pytest.fixture
def access_tester(url_manager, data_provider, client):
    return AccessTester(url_manager, data_provider, client)
```

---

## 14. Framework Test Plan

Unit tests for the framework itself live in `tacom/contest/tests/urls/tests/`. These test the UrlManager, AccessTester, Config, and DB modules in isolation.

### 14.1 `test_config.py` -- Config Model Tests

| Test | Description |
|------|-------------|
| `test_valid_config_loads` | Load a valid YAML, verify all fields parsed correctly |
| `test_extra_field_rejected` | Config with unknown field raises ValidationError (extra="forbid") |
| `test_5xx_in_status_codes_rejected` | AccessRule with status_codes=[500] raises ValueError |
| `test_capability_validation` | Unknown capability key raises ValueError |
| `test_defaults_inheritance` | RoutePolicy with None access_rules gets defaults |
| `test_defaults_override` | RoutePolicy with explicit access_rules replaces defaults |
| `test_anonymous_no_no_access_rules` | Anonymous defaults have no_access_rules=None |
| `test_method_strategy_enum` | All four MethodStrategy values are valid |
| `test_stats_config_defaults` | StatsConfig defaults are correct |

### 14.2 `test_url_manager.py` -- UrlManager Tests

Requires Django test environment (URL resolver). Uses a minimal `urls.py` with known patterns.

| Test | Description |
|------|-------------|
| **Discovery** | |
| `test_discover_finds_all_urls` | All URLPatterns from test urls.py are discovered |
| `test_discover_extracts_namespace` | Namespaced URLs have correct namespace |
| `test_discover_extracts_methods_cbv` | CBV methods correctly identified (e.g., ListView → [GET]) |
| `test_discover_extracts_methods_fbv` | FBV defaults to [GET] |
| `test_exclude_by_app` | URLs from excluded app are filtered out |
| `test_exclude_by_namespace` | URLs from excluded namespace are filtered out |
| `test_exclude_by_name` | Specific URL names are filtered out |
| `test_exclude_by_module` | URLs from excluded module are filtered out |
| **Categorization** | |
| `test_categorize_anonymous` | URLs in anonymous config are categorized correctly |
| `test_categorize_logged_in` | URLs in logged_in config are categorized correctly |
| `test_categorize_by_capability` | URLs with correct subcategory |
| `test_categorize_by_group` | URLs with correct subcategory |
| `test_categorize_parked` | Parked URLs are recognized |
| `test_categorize_missed` | URLs not in any group are "missed" |
| `test_url_in_multiple_groups_warning` | Validation warns if same URL in 2+ groups |
| **Policy Resolution** | |
| `test_get_policy_with_defaults` | Policy with None fields gets defaults |
| `test_get_policy_with_override` | Policy with explicit fields overrides defaults |
| `test_get_policy_anonymous_no_denial` | Anonymous policy never has no_access_rules |
| **Method Strategy** | |
| `test_all_from_view` | Returns view's methods |
| `test_restrict_to_config` | Returns intersection |
| `test_force_config` | Returns config methods |
| `test_extend_from_config` | Returns union |
| **Missed/Parked** | |
| `test_get_missed_count` | Correct count of unconfigured URLs |
| `test_get_missed_report_format` | Report groups by module/namespace |
| `test_get_parked` | Returns parked URLs |
| **Stats** | |
| `test_record_visit` | Visit appended to in-memory list |
| `test_soft_threshold_warning` | Warning emitted when response time exceeds threshold |
| `test_get_stats_summary` | Aggregation is correct (avg, outliers, etc.) |

### 14.3 `test_access_tester.py` -- AccessTester Tests

Uses mock Client and mock UrlManager to test validation logic in isolation.

| Test | Description |
|------|-------------|
| **Validation** | |
| `test_any_success_passes_on_200` | any_success=True + 200 → passed |
| `test_any_success_passes_on_301` | any_success=True + 301 → passed |
| `test_any_success_fails_on_403` | any_success=True + 403 → failed |
| `test_status_code_match_passes` | status_codes=[200] + 200 → passed |
| `test_status_code_mismatch_fails` | status_codes=[200] + 403 → failed |
| `test_redirect_to_allowed_target_passes` | 302 + follow → final URL in allowed_redirect_targets → passed |
| `test_redirect_to_wrong_target_fails` | 302 + follow → final URL NOT in targets → failed |
| `test_redirect_ignores_query_params` | `/login/?next=/foo` matches `account_login` |
| `test_no_302_means_no_follow` | Without 302 in codes, follow=False |
| `test_302_means_follow` | With 302 in codes, follow=True |
| **User Setup** | |
| `test_anonymous_user_logs_out` | user=None calls client.logout() |
| `test_user_force_login` | user provided calls client.force_login() |
| **Stats Recording** | |
| `test_visit_recorded_on_access` | test_access() records a VisitRecord |
| `test_visit_recorded_on_denial` | test_denial() records a VisitRecord |
| `test_response_time_tracked` | VisitRecord.response_time_ms > 0 |
| **TestResult** | |
| `test_result_contains_all_fields` | TestResult has url, method, user_type, reason, etc. |
| `test_result_includes_redirect_chain` | Chain populated when redirects followed |

### 14.4 `test_db.py` -- SQLite Tracking Tests

Uses temporary database file.

| Test | Description |
|------|-------------|
| `test_schema_created` | Tables exist after init |
| `test_persist_run_creates_record` | test_run row created |
| `test_category_snapshot_saved` | run_url_category rows for each URL |
| `test_visit_records_saved` | visit rows for each recorded visit |
| `test_cleanup_on_start_truncates` | cleanup_on_start=True clears all tables |
| `test_append_mode_preserves` | cleanup_on_start=False keeps existing runs |
| `test_default_db_path` | DB created in config.yaml directory |
| `test_custom_db_path` | DB created at configured path |
| `test_run_label_stored` | Label retrievable from test_run |
| `test_multiple_runs_tracked` | Multiple persist_run calls create separate runs |
| `test_concurrent_writes` | Two writers don't corrupt (xdist simulation) |

---

## 15. Open Questions

### 15.1 POST Success Detection

**Context:** POST to a form that succeeds typically returns 302 to a success URL. This is the same status code as "access denied redirect."

**Proposed approach for v0.2:** For `access_rules` on POST:
- If `any_success=True`: treat 302 as success (don't validate target)
- If explicit `status_codes: [302]` with `allowed_redirect_targets`: validate redirect target
- The DataProvider can optionally submit valid form data for POST tests, or tests can send empty POST (expecting form validation error 200, which is still "has access")

**Question:** Is sending an empty POST body (which returns 200 with form errors) acceptable as "has access" proof for v0.2? This avoids needing form-specific test data for every POST URL.

### 15.2 Method Extraction Accuracy for CBVs

Django's CBV base `View` class technically defines `get`, `post`, `put`, etc. handlers (they return 405). The "actually handled" check needs to verify the method is overridden in a subclass, not just present.

**Proposed approach:** Check if the method is defined on the specific view class or any of its non-`View` ancestors (e.g., `UpdateView.post` counts, but `View.post` does not).

### 15.3 Anonymous Denial Tests for Non-Anonymous URLs

Currently, `anonymous` URLs have no `no_access_rules`. But when testing `logged_in` URLs, we test anonymous users against those URLs using `logged_in`'s `no_access_rules`.

**Question:** Should we also test anonymous access against `by_capability` and `by_group` URLs? The `no_access_rules` there might differ from `logged_in` defaults (e.g., capability pages might redirect to contest_detail, not login).

**Proposed approach:** Yes, test anonymous against all non-anonymous groups. Use the group's own `no_access_rules` for the assertion.

---

**End of Specification v0.2**
