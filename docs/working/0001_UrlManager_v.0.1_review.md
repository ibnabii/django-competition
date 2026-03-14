# UrlManager v0.1 Specification

**Version:** 0.1  
**Date:** 2026-03-14  
**Status:** Draft for Review

---

## 1. Executive Summary

The UrlManager system automates comprehensive access control testing across all Django URLs in the project. It discovers URLs from Django's URL resolver, categorizes them by access requirements, and generates automated tests to verify that access control works correctly for different user types (anonymous, logged-in, capability-based, group-based).

**Key Goals:**
- Zero-configuration URL discovery from Django
- Declarative access control testing via YAML configuration
- Automatic detection of unconfigured URLs
- Support for redirect validation
- Comprehensive test coverage with minimal maintenance


---

## 2. Architecture Overview

### 2.1 Component Structure

```
tacom/contest/tests/urls/
├── models/
│   ├── url_manager.py      # Core UrlManager class
│   ├── config.py           # Pydantic configuration models (existing)
│   └── url_test_case.py    # Test case representation (new)

├── utils/
│   ├── load_config.py      # YAML config loader (existing)
│   ├── get_url_manager.py  # Factory function (existing)
│   └── url_resolver.py     # Django URL discovery (new)
├── config.yaml             # Main configuration file (existing)
└── test_url_access.py      # Pytest test suite (new)
```
> **[COMMENT]**: 
> I do not think I need 'Test case representation' - I will write tests just like all the others with pytest and Django.
> The goal here is to get an UrlManager that will be used in TestCase's Data Setup.

### 2.2 Data Flow

```
Django URL Resolver
        ↓
[URL Discovery & Extraction] → Raw URL list with metadata
        ↓
[Configuration Loading] → Access rules from YAML
        ↓
[URL Categorization] → URLs grouped by access requirements
        ↓
[Test Generation] → Pytest test cases
        ↓
[Test Execution] → HTTP requests with different user types
        ↓
[Validation & Reporting] → Pass/Fail + Statistics
```

### 2.3 Existing Implementation Analysis

**Current State:**
- ✅ Configuration models (Config, RoutePack, RoutePolicy, AccessRule) - well-designed
- ✅ YAML loader with validation
- ✅ list_urls management command for URL discovery **[COMMENT: actually the management command can be used as inspiration, but i want tests.urls module to be copiable to other projects, hence it must contain everything needed to work. Url manager needs it's own tool to traverse Django's urls]**
- ⚠️ UrlManager model exists but is minimal (needs expansion)
- ❌ No URL categorization logic
- ❌ No test generation  **[COMMENT: I do not expect to generate tests here. I will write generic test cases using Url configuration (ex. check urls defined as inteded for anonymous users, if they are really accessible by anonymous. Check if urls intended for logged in users, are not accessible for anonymous, and accessible for logged in)]**
- ❌ No statistics collection

**Building On:**
- Pydantic models provide excellent foundation
- Capability validation via dynamic import is solid
- AccessRule design supports both positive and negative testing

---

## 3. Configuration Schema Design

### 3.1 YAML Structure (Enhanced)

```yaml
# Exclusions - URLs to skip entirely
exclude:
  apps:                   # Django apps to exclude (e.g., admin, debug_toolbar)
    - "admin"
    - "debug_toolbar"
  modules:                # URL modules to exclude
    - "django.conf.urls.i18n"
  names:                  # Specific URL names to exclude
    - "account_logout"
  namespaces:             # URL namespaces to exclude (NEW)
    - "rosetta"

# Capability configuration
capability_class: "contest.permissions.capabilities.Capability"

# Group defaults (NEW) - default access rules for each category
defaults:
  anonymous:
    no_access_rules:
      - status_codes: [302]
        allowed_redirect_targets:
          - namespace: ""
            names: ["account_login"]
  
  logged_in:
    no_access_rules:
      - status_codes: [403, 404]
  
  by_capability:
    no_access_rules:
      - status_codes: [302]
        allowed_redirect_targets:
          - namespace: "contest"
            names: ["contest_detail", "contest_list"]
  
  by_group:
    no_access_rules:
      - status_codes: [403]

# Anonymous access - no login required
anonymous:
  - routes:
      - names: ["home", "about", "contact"]
    # Uses defaults.anonymous if not specified
  
  - routes:
      - namespace: "account"
        names: ["login", "signup"]
    access_rules:
      - any_success: true
    no_access_rules:  # Override default
      - status_codes: [404, 500]  # Should never redirect

# Logged-in access - any authenticated user
logged_in:
  - routes:
      - namespace: "contest"
        names: ["entry_create", "entry_list"]
    # Uses defaults.logged_in

# Capability-based access
by_capability:
  JUDGE_FINALS:
    - routes:
        - namespace: "contest"
          names: ["judging_finals", "scoresheet_create"]
      # Uses defaults.by_capability
    
    - routes:
        - namespace: "contest"
          names: ["judging_finals_submit"]
      access_rules:
        - status_codes: [200, 201]  # Explicit success codes
      no_access_rules:
        - status_codes: [302]
          allowed_redirect_targets:
            - namespace: "contest"
              names: ["judging_finals"]  # Redirect back to list page

  VIEW_SCORESHEET:
    - routes:
        - namespace: "contest"
          names: ["scoresheet_view"]

# Group-based access
by_group:
  staff:
    - routes:
        - namespace: "contest"
          names: ["admin_dashboard"]

# Unassigned - URLs to be configured later (ignored in tests)
unassigned:
  - namespace: "contest"
    names: ["experimental_feature"]

# Test execution settings (NEW)
test_settings:
  follow_redirects: false  # Default for access testing
  timeout: 5               # Request timeout in seconds
  collect_stats: true      # Enable statistics collection
  methods_to_test:         # Which HTTP methods to test
    - GET
    - POST
  skip_slow_tests: false   # Skip tests marked as slow
```
>  **[COMMENT]**: Actually 'anonymous' are urls intended to be accessible by anonymous users.
> So 'no_access_rules' is not expected to be here, as those will not be tested for restricting access,
> only checked if indeed anonymous users can access them.
> 
> Furthermore allowing 302 means, redirection is expected, when user does not have access to the page.
> but in fact everyone has access to the page.
> 
> Also think if that overrides or extends configuration? Or maybe if configuration of specific RoutePolicy will
> override, or extend default? For some tests I might expect 302 not to be allowed, rather expecting straight 403 or 404.
> Eg. for some urls in logged_in group, when testing with anonymous user, expectation might be to hit 404, or 403, but
> on some urls it might be expected that user is redirected to login page.
> 
> The expectation in general is that absence of 302 in status_codes means that request will not follow redirects, as redirect
> is not allowed, and
> - for access_rules - status_codes expected to be returned are exactly those specified (unless any_success = True, where any request.ok will do), but directly at requested url
> - for no_access_rules - user should get 403 or 404 (or anything specfied in  status_codes immediatelly 
> If 302 is present, then url will be called with follow_redirects=True, and the chain is expected to end with 
> request.ok on one of the target.
> 
> Furthermore status 500 is never expected to be used in no_access_rules, as it would mean, that generating
> internal server error (500) is expected when user without anticipated url access tries to enter url.
> 
> To sum app: access_rules define outcome of successfull 'i am expected to be allowed to access this url' test is,
> while no_access_rules define outcome of 'i am expected to be denied to access this url' test succesfful outcome
> (ie. how user with no access rights is expected to be denied access).
>
 
### 3.2 Configuration Model Enhancements

**New Models:**

```python
class ExcludeConfig(BaseModel):
    apps: list[str] = []
    names: list[str] = []
    modules: list[str] = []
    namespaces: list[str] = []  # NEW **[COMMENT: OK]**

class DefaultRules(BaseModel):
    """Default access rules for a category"""
    access_rules: list[AccessRule] = [AccessRule(any_success=True)]
    no_access_rules: list[AccessRule] = [AccessRule(status_codes=[401, 403, 404])]

class DefaultsConfig(BaseModel):
    """Group-level defaults"""
    anonymous: DefaultRules = DefaultRules()
    logged_in: DefaultRules = DefaultRules()
    by_capability: DefaultRules = DefaultRules()
    by_group: DefaultRules = DefaultRules()
```
> **[COMMENT]**: So here i asume that default rules for particular group will be applied, if particular RoutePolicy does
> not specify access_rules or no_access_rules. In such case the unspecified one is used from defaults? Please elaborate on this
> in next document version.
>
```python
class TestSettings(BaseModel):
    """Test execution configuration"""
    follow_redirects: bool = False  **[COMMENT: As mentioned before, each url will be tested with or without follow_redirects depending on presence of 302 in status_codes for access/no_access]**
    timeout: int = 5 **[COMMENT: OK]**
    collect_stats: bool = True  **[COMMENT: OK]**
    methods_to_test: list[str] = ["GET", "POST"]  **[COMMENT: Actually i expect the 'url crawler' to findo out what methosds are exposed by each of the urls, and methods exposed will be tested per url]**
    skip_slow_tests: bool = False  **[COMMENT: Not sure if this is needed]**

class Config(BaseModel):
    # Existing fields...
    exclude: ExcludeConfig
    anonymous: list[RoutePolicy] = []
    logged_in: list[RoutePolicy] = []
    unassigned: list[RoutePack] = []
    capability_class: str | None = None
    by_capability: dict[str, list[RoutePolicy]] = {}
    by_group: dict[str, list[RoutePolicy]] = {}
    
    # NEW fields
    defaults: DefaultsConfig = DefaultsConfig()
    test_settings: TestSettings = TestSettings()
```

---

## 4. UrlManager API Design

### 4.1 Core UrlManager Class

```python
from pydantic import BaseModel
from django.urls import URLPattern, URLResolver
from typing import Literal

# URL representation
class DiscoveredUrl(BaseModel):
    """A URL discovered from Django resolver"""
    path: str                    # Actual URL path (e.g., "/contest/entry/123/")  **[COMMENT: I think this duplicates with resolved URL - because how otherwise would you discover actual url? We want to get all urls from django resolver, then create test data to actually build real paths, or maybe i'm missing something?]**
    name: str                    # URL name (e.g., "entry_detail")
    namespace: str               # URL namespace (e.g., "contest")
    view_module: str             # View module path
    view_name: str               # View class/function name
    supported_methods: list[str] # HTTP methods (GET, POST, etc.)  **[COMMENT: shouldn't this be typed? so that later on tests can easily do mapping eg. using request library (or rather any async library chosen) as GET -> request.get]**
    url_pattern: str             # Django pattern (e.g., "entry/<int:pk>/")
    
    @property
    def full_name(self) -> str:
        """Returns namespace:name format"""
        return f"{self.namespace}:{self.name}" if self.namespace else self.name

class ResolvedUrl(BaseModel):
    """A URL resolved with test parameters"""
    discovered: DiscoveredUrl
    resolved_path: str           # Path with parameters filled
    test_params: dict            # Parameters used for resolution

# URL categorization
UrlCategory = Literal[
    "anonymous",
    "logged_in", 
    "by_capability",
    "by_group",
    "unassigned",  **[COMMENT: I assume this is category of URLs that were not covered by config, but discovered by url crawler?]**
    "orphaned",
    "excluded"
]

class CategorizedUrl(BaseModel):
    """A URL with its access category"""
    url: DiscoveredUrl
    category: UrlCategory
    subcategory: str | None = None  # capability name or group name
    policy: RoutePolicy | None = None  # Associated policy

```
> **[COMMENT]**: Not sure what is the purpose of this. I thougth i'd rather do something like:
> 1. Iterate throguh config groups to run tests, eg. i need different test case for anonmous-allowed urls than those for logged in users, or i need to create different test users with different setup for each by_capability or by_group.
> 2. For any url from django resolver, check if it is member of any of the groups. If not  store it and expose api to check how many (and also list of them) of such urls are there and raise error in tests in there are any.
> 3. To proceed with tests i may move those missed ones to configuration into 'orphaned' group to decide later what to do with them, and only rise warning, rather than error if api says there are any (i expect api allowes to get count, and list with urls)
```python    
    
# Statistics tracking
class UrlTestStats(BaseModel):
    """Statistics for a single URL test"""
    url: str
    method: str
    user_type: str               # anonymous, logged_in, capability:{name}, group:{name}
    status_code: int
    response_time_ms: float
    followed_redirects: bool
    redirect_chain: list[str] = []
    timestamp: datetime

class UrlManagerStats(BaseModel):
    """Aggregate statistics"""
    total_urls_tested: int
    total_requests: int
    passed_tests: int
    failed_tests: int
    avg_response_time_ms: float
    test_duration_seconds: float
    test_details: list[UrlTestStats]


class UrlManager(BaseModel):
    """
    Core URL management and testing system
    """
    config: Config
    _discovered_urls: list[DiscoveredUrl] = []
    _categorized_urls: list[CategorizedUrl] = []
    _stats: UrlManagerStats | None = None
    
    # ========================================
    # 1. URL Discovery
    # ========================================
    
    def discover_urls(self) -> list[DiscoveredUrl]:
        """
        Discover all URLs from Django's URL resolver.
        Excludes URLs based on config.exclude rules.
        
        Returns:
            List of discovered URLs with metadata
        """
        ...
    
    def _should_exclude(self, url: DiscoveredUrl) -> bool:
        """Check if URL should be excluded based on config"""
        ...
    
    def _extract_methods(self, view) -> list[str]:
        """Extract supported HTTP methods from view"""
        ...
    
    # ========================================
    # 2. URL Categorization
    # ========================================
    
    def categorize_urls(self) -> list[CategorizedUrl]:
        """
        Categorize discovered URLs into access groups.
        
        Returns:
            List of categorized URLs
        """
        ...
    
    def _match_route(self, url: DiscoveredUrl, route_pack: RoutePack) -> bool:
        """Check if URL matches a RoutePack specification"""
        ...
    
    def get_urls_by_category(
        self, 
        category: UrlCategory,
        subcategory: str | None = None
    ) -> list[CategorizedUrl]:
        """
        Get all URLs in a specific category.
        
        Args:
            category: Main category (anonymous, by_capability, etc.)
            subcategory: Optional subcategory (capability name, group name)
        
        Returns:
            Filtered list of categorized URLs
        """
        ...
    
    # ========================================
    # 3. Unconfigured URL Detection
    # ========================================
    
    def get_unconfigured_urls(self) -> list[DiscoveredUrl]:
        """
        Get URLs that are not configured in any category.
        
        Returns:
            List of orphaned URLs
        """
        ...
    
    def get_unconfigured_count(self) -> int:
        """Count of unconfigured URLs"""
        ...
    
    def report_unconfigured_urls(self) -> str:
        """
        Generate human-readable report of unconfigured URLs.
        Groups by module, namespace, etc.
        
        Returns:
            Formatted report string
        """
        ...
    
    # ========================================
    # 4. URL Resolution (for testing)
    # ========================================
    
    def resolve_url(
        self, 
        url: DiscoveredUrl,
        params: dict | None = None
    ) -> ResolvedUrl:
        """
        Resolve URL pattern to actual path with test parameters.
        
        Args:
            url: URL to resolve
            params: URL parameters (or auto-generate if None)
        
        Returns:
            Resolved URL with test path
        """
        ...
    
    def _generate_test_params(self, url: DiscoveredUrl) -> dict:
        """
        Auto-generate parameters for URL pattern.
        E.g., <int:pk> -> {"pk": 1}
        """
        ...
    
    # ========================================
    # 5. Test Case Generation
    # ========================================
    
    def generate_test_cases(self) -> list[UrlTestCase]:
        """
        Generate test cases for all configured URLs.
        
        Returns:
            List of test cases ready for execution
        """
        ...
    
    def _create_test_case(
        self,
        categorized_url: CategorizedUrl
    ) -> list[UrlTestCase]:
        """
        Create test cases for a single categorized URL.
        Generates multiple test cases (one per method, user type).
        """
        ...
    
    # ========================================
    # 6. Access Testing
    # ========================================
    > **[COMMENT]**: This is worth discussing. Actually i thought tests themselves will hande usch thing, ie it's test that know that:
    > for urls in anonymous: test if anonymous can access it,
    > for urls in logged_in: test if logged_in can access it, and anonymous cannot
    > for urls in by_capability: test if user with capability for that competition (compare next paragraph about permissions and requried setyup)
    > can access it, while anonymous or logged in without capability or with capabilty but for different competition cannot
    > and UrlManager would only be source of urls, expected outcomes of both "check if can access" and "check if cannot access" cases
    > and would accept back feedback like 'i have visited this particular url and did it in that time, with this method, this user type,
    > and tests will run assertions raising errors if anything goes differently than expected.
    > maybe (to be discussed) UrlManager and it's config would also store/expose functions to build particular urls, i am not sure
    > where to put logic like:
    > if url pattern has <slug:contest_slug> in it, that means i need to: create a contest and use it to build real path, and also
    > if url is marked as by_capability, then user must be granted this capability for this contest - however fact that capabilities
    > are defined per contest is specific to this project, and other projects that will use this module in the future might have different 
    > persmissions model, it would be best to be able to define a class/function in the config, that will point to specific implementation,
    > so that config and whole engine is reusable, while specific clases/functions can be implemented in project specific way and
    > only referred by configuation        
    
    
    def test_url_access(
        self,
        url: ResolvedUrl,
        user_type: str,
        method: str,
        expected_access: bool,
        policy: RoutePolicy | None = None
    ) -> UrlTestResult:
        """
        Test access to a URL with specific user type and method.
        
        Args:
            url: Resolved URL to test
            user_type: Type of user (anonymous, logged_in, capability:{name}, etc.)
            method: HTTP method (GET, POST, etc.)
            expected_access: Whether access should be granted
            policy: Access policy with rules
        
        Returns:
            Test result with pass/fail status
        """
        ...
    
    def _validate_access(
        self,
        response,
        expected_access: bool,
        rules: list[AccessRule]
    ) -> tuple[bool, str]:
        """
        Validate response against access rules.
        
        Returns:
            (passed, reason) tuple
        """
        ...
    
    def _check_redirect_target(
        self,
        redirect_url: str,
        allowed_targets: list[RoutePack]
    ) -> bool:
        """Check if redirect target is allowed"""
        ...
    
    # ========================================
    # 7. Statistics & Reporting
    # ========================================
    
    def collect_stats(self, test_result: UrlTestResult):
        """Add test result to statistics"""
        ...
    
    def get_stats(self) -> UrlManagerStats:
        """Get aggregate statistics"""
        ...
    
    def reset_stats(self):
        """Reset statistics collection"""
        ...
    
    # ========================================
    # 8. Utility Methods
    # ========================================
    
    def get_summary(self) -> dict:
        """
        Get summary of URL categorization.
        
        Returns:
            {
                "total": 150,
                "anonymous": 10,
                "logged_in": 40,
                "by_capability": {"JUDGE_FINALS": 5, "VIEW_SCORESHEET": 3},
                "by_group": {"staff": 2},
                "unassigned": 0,
                "orphaned": 90,
                "excluded": 15
            }
        """
        ...
    
    def validate_config(self) -> list[str]:
        """
        Validate configuration for common issues.
        
        Returns:
            List of warning/error messages
        """
        ...
```

### 4.2 Supporting Models

```python
class UrlTestCase(BaseModel):
    """Represents a single test case"""
    url: ResolvedUrl
    method: str
    user_type: str
    expected_access: bool
    policy: RoutePolicy | None
    test_name: str  # pytest test name

class UrlTestResult(BaseModel):
    """Result of a single URL test"""
    test_case: UrlTestCase
    passed: bool
    status_code: int
    response_time_ms: float
    reason: str
    redirect_chain: list[str] = []
    timestamp: datetime
```
> **[COMMENT]**: DO i need it given, that some of the logic will be placed in tests? Consider this as archictecure point that needs
> carefull attention.
---

## 5. URL Categorization Logic

### 5.1 Categorization Algorithm

```
For each discovered URL:
    1. Check if excluded → category = "excluded", SKIP
    2. Check if in unassigned → category = "unassigned", CONTINUE
    3. Check if matches anonymous routes → category = "anonymous"
    4. Check if matches logged_in routes → category = "logged_in"
    5. Check if matches by_capability routes → category = "by_capability", set subcategory
    6. Check if matches by_group routes → category = "by_group", set subcategory
    7. If no match → category = "orphaned"
```

### 5.2 Route Matching

A URL matches a RoutePack if:
- `url.namespace == route_pack.namespace` (if namespace specified)
- `url.name in route_pack.names`

**Edge Cases:**
- Empty namespace in RoutePack matches URLs with no namespace
- Multiple RoutePacks can match (first match wins)
- Same URL can appear in multiple policies (validation warning)  **[COMMENT: Good point!]**

### 5.3 Orphaned vs Unconfigured

**Unconfigured URLs** = `orphaned` + `unassigned`

- **Orphaned:** URLs not mentioned anywhere in config (should be configured)
- **Unassigned:** URLs explicitly marked as "to be configured later" (ignored in tests)
**[COMMENT: Actually i thougth otherway around, but maybe you're right. Please think if better names could be used, eg missed and temporarily_ignored?]**
---

## 6. Access Control Test Scenarios

### 6.1 Positive Testing (Can Access)

For each URL in a category, test that authorized users CAN access:

| Category | Test User | Expected Result |
|----------|-----------|-----------------|
| anonymous | Anonymous (not logged in) | Success (200, 201, etc.) or allowed redirect |
| logged_in | Logged-in user (any) | Success or allowed redirect |
| by_capability/{cap} | User with capability {cap} | Success or allowed redirect |
| by_group/{group} | User in group {group} | Success or allowed redirect |

**Success Criteria:**
1. `any_success=true`: Any 2xx or 3xx status code
2. `status_codes` list: Response code in allowed list
3. `allowed_redirect_targets`: If redirect (302), target must be in allowed list

### 6.2 Negative Testing (Cannot Access)

For each URL, test that unauthorized users CANNOT access:

| Category | Test Users (should be denied)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Expected Result                                                     |
|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------|
| anonymous | N/A (already accessible)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | N/A                                                                 |
| logged_in | Anonymous user                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 401/403/404 or redirect to login **[COMMENT: dependign on Policy]** |
| by_capability/{cap} | Logged-in user WITHOUT capability **[COMMENT: Or with capability, but defined for different contest. Capabilties are defined for contest, user pairs in this project - see before for comments, this needs to be handled somehow configuration wise (or maybe it's just test that should know about that, in such case i'd have generic tests that i can easily reuse in other project, jus subjkect to configuation, and specific ones that i need to re-write in other projects. BUt i'd rather have full generic solution only pointing to specific classes for project-specific configuration]** | 403/404 or redirect to safe page                                    |
| by_group/{group} | Logged-in user NOT in group   **[COMMENT: This part oposed to capabitilites is fully reusable as groups are concept native to Django]**                                                                                                                                                                                                                                                                                                                                                                                                                                                              | 403/404 or redirect to safe page                                    |

**Failure Criteria (from `no_access_rules`):**
1. `status_codes` list: Response code must be in denied list
2. `allowed_redirect_targets`: If redirect, must go to login or safe page **[COMMENT: If redirect, must go to any of defined targets, but yes, for most cases, especially in logged_in group, this will be login page (but other scenarios are also possible)]**

### 6.3 Test Matrix Example

For URL: `contest:judging_finals` (requires JUDGE_FINALS capability)

| User Type                 | Method | Expected Access | Expected Response |
|---------------------------|--------|-----------------|-------------------|
| Anonymous                 | GET | ❌ No | 302 → account:login |
| Logged-in (no cap)        | GET | ❌ No | 302 → contest:contest_list |
| Logged-in (JUDGE_FINALS **[COMMENT: in same competition as passed in url - see other commments on my permissions system]**) | GET | ✅ Yes | 200 | 
| Logged-in (JUDGE_FINALS) **[COMMENT: in same competition as passed in url - see other commments on my permissions system]** | POST | ✅ Yes | 200/201/302 → self |  
> **[COMMENT]**: Other scenarios:
> | Logged-in (OTHER_CAP) in same competition| ANY | ❌ No |...|
> | Logged-in (JUDGE_FINALS) in other competition| ANY | ❌ No |...|
> | Logged-in (OTHER_CAP) in same competition| ANY | ❌ No |...|

> **[COMMENT]**: Other note on permissions:
> Giving it a second thought i think i will need also custom setup, give it a deeper thought. I need to define for some urls
> class/function (and reference it in the config) that will contain more custom logic. For instance i have urls,
> where in general they look like standard GET resource, but they are expected to work only if user 'owns' the resoure in some,
> sometimes quite complicated way. Most complex example i can think of now: user has Entry, Entry belongs to Category, which Belongs
> to Compettion, and this Entry is handeld by some Package (technical concept), thus user accessing GET /package/{package_id} 
> or GET /packages/{contest_id} must have those connections, and i think there is no way to define it in config, rather
> than pointing to some class/function that will handle it. Possibly (but feel free to propose something here) exposing API to
> create a dataset and return user that will be succesffull for particular resolved (real, with real ids) url on one hand, 
> unsuccesfull on the other hand, and maybe actually a list of users, as they may be granted/denied access in way more complicated way.
> Or maybe for version one i'm overcomplicating and (sticking to the package example), as it is not related to capabilty/group,
> I will only have class producing valid url and user, everything else needs to be denied, and details of ownership reauires
> own tests outside of this framework, which needs to be as re-usable and automatic as possible. I'm leaning towards the latter appraoach.

### 6.4 HTTP Method Testing

By default, test all methods returned by `_extract_methods()`:
- Read-only views: GET only
- Forms: GET (display), POST (submit)
- APIs: GET, POST, PUT, PATCH, DELETE
> **[COMMENT]**: Note that this needs to identify actually handled paths, as declarative appraoch may not work
> I use Class Based Views a lot, and declaratively all Views in django handle all methods, but actually eg UpdateView
> In reality does only handle GET and POST (and maybe PUT and PATCH - not sure),
> and DeleteView only handles DELETE.
> The framework may actually be extended to test all methods, but automatically expecting 405 Method Not Allowed response
> for all users, for methods that the View does not actually work with. This would align well with config item below
> so that i can only tesdt GET and POST if my app uses web-views, while all if it's a DRF API - rethink it and decide best
> on best practices.

Can be filtered via `config.test_settings.methods_to_test`

---

## 7. Redirect Validation Approach

### 7.1 Redirect Scenarios

**Scenario 1: Login redirect (unauthorized)**
```yaml
no_access_rules:
  - status_codes: [302]
    allowed_redirect_targets:
      - namespace: ""
        names: ["account_login"]
```
- Anonymous user → 302 to `/accounts/login/`
- Validate: redirect target is `account_login`

**Scenario 2: Safe redirect (insufficient permissions)**
```yaml
no_access_rules:
  - status_codes: [302]
    allowed_redirect_targets:
      - namespace: "contest"
        names: ["contest_detail", "contest_list"]
```
- Logged-in user without capability → 302 to contest list/detail
- Validate: redirect target is one of allowed URLs

**Scenario 3: Success redirect (POST form)**
```yaml
access_rules:
  - status_codes: [302]
    allowed_redirect_targets:
      - namespace: "contest"
        names: ["entry_detail"]
```
- POST to entry_create → 302 to entry_detail (created object)
- Validate: redirect target is expected success page
> **[COMMENT]**: Not sure about the last one, POST form redirect is very common scenario, and i need to distinguish following cases:
> 1. User has permissions (no matter how - this depends on category of url), and gets redirected, and maybe i should have non-string to put her 'same url'?,
> 2. User does not have permissions to POST, but he's redirected to GET which is accessible anonymously? Is this case even possible? Let's dicuss it

### 7.2 Redirect Validation Algorithm

```python
def _check_redirect_target(redirect_url: str, allowed_targets: list[RoutePack]) -> bool:
    # Resolve redirect_url to namespace:name
    resolved = resolve(redirect_url)
    
    for target in allowed_targets:
        if resolved.namespace == target.namespace:
            if resolved.url_name in target.names:
                return True
    
    return False
```

### 7.3 Redirect Chain Tracking

- By default: `follow_redirects=False` (test first response only)
- If `302` in `status_codes`: Enable following redirects
- Track entire chain: `/entry/create/` → `/accounts/login/` → final page
- Validate final destination against `allowed_redirect_targets`

---

## 8. Statistics Collection Mechanism

### 8.1 Per-Request Metrics

For each URL test, collect:
- URL path
- HTTP method
- User type (anonymous, logged_in, capability:X) **[COMMENT: and group: X]** 
- Status code
- Response time (ms)
- Redirect chain
- Timestamp

> **[COMMENT]**: Also i think i'd need (and configured?) max allowed response time:
> 1. Soft that will raise warinig if response time is too high
> 2. Hard that will raise error if response time is too high
> Or maybe soft is enoght for version 1?

### 8.2 Aggregate Metrics

Summary statistics:
- Total URLs tested
- Total HTTP requests made
- Pass/fail counts
- Average response time
- Slowest URLs (top 10) 
- Test duration

> **[COMMENT]**: Slowest URLs and also URls that are away from others, think and proposed some metrics
> Immediatelly i can think of something like (but not sure if it's the best ppraoch here, i'm posting thenm just as examples)
> 1. URLs with average response time being longer than one standard deviation from the rest
> 2. URLS with response times varuing largely (inconsitent results suggest they might have n^2 complexity)

### 8.3 Reporting Formats
> **[COMMENT]**: Not sure here, i run pararell pytest workers usually, so console output might be
> not that useful, but maybe depending on programatically set paramter of UrlManager (during data setup)
> it could log to file, or sqlite database?
 

**Console Output (during tests):**
```
Testing contest:entry_create [GET]
  ✅ Anonymous → 302 (login redirect) [45ms]
  ✅ Logged-in → 200 [38ms]

Testing contest:judging_finals [GET]
  ✅ Anonymous → 302 (login redirect) [41ms]
  ✅ Logged-in (no cap) → 302 (safe redirect) [52ms]
  ✅ Logged-in (JUDGE_FINALS) → 200 [63ms]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 150 URLs tested, 450 requests
  Passed: 445 (98.9%)
  Failed: 5 (1.1%)
  Avg response time: 47ms
  Duration: 23.4s
```

**JSON Export:**
```json
{
  "summary": {
    "total_urls": 150,
    "total_requests": 450,
    "passed": 445,
    "failed": 5,
    "avg_response_time_ms": 47.2,
    "duration_seconds": 23.4
  },
  "failures": [
    {
      "url": "contest:entry_detail",
      "method": "GET",
      "user_type": "anonymous",
      "expected": "302",
      "actual": "200",
      "reason": "Expected redirect but got success"
    }
  ],
  "slowest_urls": [
    {"url": "contest:judging_finals", "method": "GET", "time_ms": 523},
    {"url": "contest:entry_create", "method": "POST", "time_ms": 412}
  ]
}
```

---

## 9. Example Configurations

### 9.1 Simple Anonymous Pages

```yaml
anonymous:
  - routes:
      - names: ["home", "about", "contact", "faq"]
    access_rules:
      - any_success: true
    no_access_rules:
      - status_codes: [500, 503]  # Should never error
```
> **[COMMENT]**: No, we're not on the same page on no_access_rules, this has been already explained in earlier comments.
> no_access_rules is meant as positive validation of acceess beeing denied, anonymous pages are not
> exected to fail access at any point, so no_access_rules is not needed here.
> Also 5xx codes mean something went wrong - in no case this is expected behvaior for handling unauthorized access attempt
 
### 9.2 Login-Required with Redirect

```yaml
logged_in:
  - routes:
      - namespace: "contest"
        names: ["entry_create", "entry_list", "entry_update"]
    access_rules:
      - any_success: true
    no_access_rules:
      - status_codes: [302]
        allowed_redirect_targets:
          - names: ["account_login"]
```

### 9.3 Capability-Based Access

```yaml
by_capability:
  JUDGE_FINALS:
    - routes:
        - namespace: "contest"
          names: ["judging_finals_list", "judging_finals_detail"]
      access_rules:
        - status_codes: [200]
      no_access_rules:
        - status_codes: [302]
          allowed_redirect_targets:
            - namespace: "contest"
              names: ["contest_detail"]  # Redirect to contest home
  
  VIEW_SCORESHEET:
    - routes:
        - namespace: "contest"
          names: ["scoresheet_view"]
      access_rules:
        - status_codes: [200]
      no_access_rules:
        - status_codes: [403]  # Hard deny (no redirect)
```

### 9.4 POST with Success Redirect
> **[COMMENT]**: See my previous comment on post. We need to distinguis between redirects on success and redirects on noaccess,
> propose a way to do this in the most generic way.
> Maybe the pareto rule 80:20 we can assume POST with access success by inspecting if View runs success_url, 
> or if the object was actually created/modified.

```yaml
logged_in:
  - routes:
      - namespace: "contest"
        names: ["entry_create"]
    access_rules:
      - status_codes: [302]  # Successful POST redirects
        allowed_redirect_targets:
          - namespace: "contest"
            names: ["entry_detail", "entry_list"]
    no_access_rules:
      - status_codes: [302]
        allowed_redirect_targets:
          - names: ["account_login"]
```

### 9.5 Group-Level Defaults

```yaml
defaults:
  by_capability:
    access_rules:
      - status_codes: [200, 201]
    no_access_rules:
      - status_codes: [302]
        allowed_redirect_targets:
          - namespace: "contest"
            names: ["contest_detail", "contest_list"]

by_capability:
  JUDGE_FINALS:
    - routes:
        - namespace: "contest"
          names: ["judging_finals"]  # Uses defaults
    
    - routes:
        - namespace: "contest"
          names: ["judging_finals_submit"]
      # Override defaults for this specific URL
      access_rules:
        - status_codes: [200, 302]
          allowed_redirect_targets:
            - namespace: "contest"
              names: ["judging_finals"]
```

---
> **[COMMENT]**: Below section needs to be re-written upon resolving comments, as some design changes are likely
> I will review this section in next version.
## 10. Implementation Roadmap

### Phase 1: Core Discovery & Categorization
1. Implement `discover_urls()` using Django resolver
2. Implement `categorize_urls()` with route matching
3. Implement `get_unconfigured_urls()` and reporting
4. Write unit tests for categorization logic

### Phase 2: Configuration & Validation
1. Enhance Config models with defaults and test_settings
2. Implement `validate_config()` for common issues
3. Add configuration inheritance (defaults → policy overrides)
4. Write configuration validation tests

### Phase 3: Test Generation
1. Implement URL resolution with auto-parameter generation
2. Implement `generate_test_cases()`
3. Create user fixtures (anonymous, logged-in, with capabilities)
4. Write test generation tests

### Phase 4: Access Testing
1. Implement `test_url_access()` with HTTP client
2. Implement access validation logic
3. Implement redirect validation
4. Write integration tests

### Phase 5: Statistics & Reporting
1. Implement statistics collection
2. Implement console reporter
3. Implement JSON export
4. Add performance tracking

### Phase 6: Pytest Integration
1. Create `test_url_access.py` test suite
2. Implement parametrized tests
3. Add pytest markers (@pytest.mark.url_access)
4. Add CLI options (--url-stats, --unconfigured-only)

---

## 11. Open Questions & Clarifications Needed

### 11.1 URL Parameter Resolution

**Question:** How should URL parameters be resolved for testing?

**Options:**
1. **Auto-generate dummy values:** `<int:pk>` → `pk=1`, `<slug:slug>` → `slug="test"`
   - **Pros:** Fully automated, no configuration needed
   - **Cons:** May not work if DB is empty (404s expected)

2. **Require test fixtures:** Load test data before URL tests
   - **Pros:** Tests real data, realistic scenarios
   - **Cons:** Requires fixture setup, slower

3. **Mock resolution:** Don't actually call URLs, just validate routing
   - **Pros:** Fast, no DB needed
   - **Cons:** Doesn't test actual access control

**Recommendation:** Option 2 (require fixtures), with Option 1 as fallback for simple cases.
> **[COMMENT]**: Maybe mixed version 2 - provide a reference in config to class/function that will handel
> this for a group of urls? Not sure how to handle this so you need to deeply investigate it, but one scenario
> i can think of is reference a class/function for DB setup, but API contract needs to be defined, well-designed
> to be as robust and re-usable as possible, eg. this could reference a class that setups a contest, and users in one function
> while in other returns user (and creates it if necessary) with particular condition, eg. list or dictionaries
> of users having certain traints such as having apritcular capability(ies0 in particular contests), but how would API work here?
> maybe the class would held all the logic, and the test would only ask: i have this url, marked as by_capability:X, and in response get:
> 1. resolved (real, callable) url
> 2. list of users that are expected to successfullyc all this url
> 3. list of users that are expected to fail this url
> so the class would be a place that knows, that capability is per contest, and hearing 'url pattern x, capabilityu Y'
> would create whatever is needed to resolve this url (in most cases contest, but also other object), and user with roles
> having this capability (where to put logic resolving capability to roles? this setup is specific for project, so mayb in this class)
> for the contest and return them as (2), and on (3) list retunr users with other capabilities, anonymous, with same
> capability for other contest than one referenced by resolved URL
>
**User Input Needed:**
- Do you have existing fixture factories (factory_boy)?
> **[COMMENT]**: I have for most central concepts of the system, but not all
- Should URL tests require specific test data setup?
> **[COMMENT]**: I think so -see the long comment above 
- What happens for URLs that require specific objects (e.g., `/contest/123/`)?
> **[COMMENT]**: Object needs to exist in DB,
### 11.2 Capability Context

**Question:** Some capabilities are contest-scoped (e.g., JUDGE_FINALS only for specific contest).

**Options:**
1. **Test with any valid contest:** Create test contest, test URLs with that context
2. **Test without context:** May fail if views require contest
3. **Configure test contexts in YAML:** Specify which contest/object to use

**Current Situation:**
- `CapabilityRequiredMixin` checks `request.perm.can(capability, contest)`
- URLs like `contest:judging_finals` require contest_slug parameter

**Recommendation:** Create test contest fixture, inject via middleware/context for tests.
> **[COMMENT]**: that's a good idea, or maybe the appraich outlined above is also valid? let's discuss it

**User Input Needed:**
- How are contest-scoped capabilities tested currently?
> **[COMMENT]**:no automatic tests are created yet here 
- Should we create a test contest for all capability tests?
> **[COMMENT]**: That might be an option, create two contests, add capabiliteis when required for a user to one
> and test two different urls for scenarios:
> 1. User has capability in the competition
> 2. User has capability in other competition
> while user does not have capabitly, or anonymous could be tested in either url?

- Can we use `request.contest` from middleware?
> **[COMMENT]**: request.contest only derrives contest object from url's slug, so this doesn't help
> with issue discussed in any way i think

### 11.3 Redirect Target Validation Strictness

**Question:** How strict should redirect validation be?

**Options:**
1. **Exact match:** Redirect must be exactly `account:login`
2. **Pattern match:** Redirect to any URL in `anonymous` category
3. **Flexible:** Allow any redirect if status code matches

**Example:**
```yaml
no_access_rules:
  - status_codes: [302]
    allowed_redirect_targets:
      - names: ["account_login"]
```

If user redirects to `/accounts/login/?next=/contest/entry/create/`, does this match?

**Recommendation:** Match base URL (ignore query params for redirect validation).
> **[COMMENT]**: Agreed., next is very good exemplification. Also i have some and plan to have more
> views whre query param is used eg. for sorting, and this test module is focused on access control,
> so i think it's ok to ignore query params here, i will have separate functional tests to check
> if query params are preserved or not

**User Input Needed:**
- Should query parameters be ignored for redirect matching?
> **[COMMENT]**: Yes 
- Is redirect chain validation needed (e.g., login → original URL)?
> **[COMMENT]**: No, I only care about final one, however keeping track of chain might be usefull for debugging 

### 11.4 HTTP Method Coverage

**Question:** Should all methods be tested, or only primary ones?

**Current Situation:**
- `list_urls` command extracts methods from views
- Some views have GET/POST, others have full REST methods

**Options:**
1. **Test all methods:** Complete coverage
   - **Pros:** Comprehensive
   - **Cons:** Slow, many redundant tests

2. **Test primary methods only:** GET for read, POST for write
   - **Pros:** Faster, covers 90% of cases
   - **Cons:** Might miss DELETE/PATCH permission issues

3. **Configurable per URL:**
   ```yaml
   - routes:
       - names: ["entry_create"]
     methods_to_test: ["GET", "POST"]
   ```

**Recommendation:** Option 2 (primary methods) with configurable override.
> **[COMMENT]**: Maybe this should be a global-config level settings allwoing (probably with multiple switches) following cases:
> 1. Test all methods defined at view level (test all methods that a view has, but note the method on checking it metnioed earlier, maybe reuse appraoch from my list_urls command?)
> 2. Restrict tests to a subset only (eg. GET, POST) and test only those methods, that are on view list and config list eg: (assuming (GET, POST config))
> View has GET only -> test only GET, View has GET, POST, DELETE -> test GET and POST
> 3. Force test of selected methods regardles of view definition (with a sub-option to test all methods without specifying tehm explicity), follwing previous example the same  config (GET, POST) again:
> View has GET only, or view has GET, POST, DELETE -> test GET, POST for both
> 4. Force test extension, ie test methods from config AND those, defined at view level (even if they are not in config list),
> so with the same example of config (GET, POST) again: View has GET only-> test GET and POST, View has GET, POST, DELTE -> test all 3
> 


**User Input Needed:**
- Are DELETE/PUT/PATCH methods used in views?
> **[COMMENT]**: I beleive at least DELETE is
- Should API endpoints be tested differently?
> **[COMMENT]**: I think the approach outlined above is very robust. I do not have any API endpoints now, so maybe
> we can think of it in next version

### 11.5 Test Data Dependencies

**Question:** Should URL tests create their own test data, or rely on existing fixtures?

**Options:**
1. **Self-contained tests:** Each test creates needed data
   - **Pros:** Isolated, repeatable
   - **Cons:** Slow, complex setup

2. **Shared fixtures:** Use pytest fixtures for test data
   - **Pros:** Fast (setup once)
   - **Cons:** Tests not isolated

3. **Hybrid:** Minimal shared fixtures (users, contests), create specific data per test

**Recommendation:** Option 3 (hybrid approach)
> **[COMMENT]**: I do not want UrlManager to handle this, this will be handeld by tests

**User Input Needed:**
- Do you use pytest fixtures or Django fixtures?
> **[COMMENT]**: pytest fixtures are used ocassionally, but as project is in active development with
> lots of changes, so i prefer to create data programatically/ with factories to keep them in line with latest changes.
- Are there existing test data factories (factory_boy)?
> **[COMMENT]**: Yes, for main entities
- Should we create minimal data or realistic data?
> **[COMMENT]**: I think realistic data is better, but I think architecturally tests will create data for themselves,
> here we're after managing urls lists and configs.

### 11.6 Performance & Parallelization

**Question:** Should tests run in parallel?

**Considerations:**
- 150 URLs × 3 user types × 2 methods = 900 HTTP requests
- Sequential: ~45 seconds (50ms per request)
- Parallel (10 workers): ~5 seconds

**Options:**
1. **Sequential:** Easier to debug, simpler
2. **Parallel with pytest-xdist:** Faster, but requires thread-safe setup
3. **Async with httpx:** Fast, complex

**Recommendation:** Start sequential, add pytest-xdist support later.
> **[COMMENT]**: I already use pytest-xdist for parallel tests, but async calls are also something i want to do, as I have many tests.

**User Input Needed:**
- Is test speed critical (CI/CD pipeline)?
> **[COMMENT]**: no
- Do tests need to run in transactions (DB isolation)?
> **[COMMENT]**: no

### 11.7 Unconfigured URL Reporting

**Question:** Should unconfigured URLs fail tests or just warn?

**Options:**
1. **Fail tests:** Force 100% configuration coverage
2. **Warn only:** Report but don't fail
3. **Configurable:** Set threshold (e.g., max 10 unconfigured URLs)

**Recommendation:** Option 2 (warn) initially, then Option 3 once stable.
> **[COMMENT]**: I think i will just have a test to assert that what now is called orphaned is zero, and fail otherwise.
> Moving those urls to unassigned (current name - subject to change per other comment) will raise warnings only, as i will
> know what exactlyt he tests are missing

> 
**User Input Needed:**
- How many unconfigured URLs are expected initially?
- Should tests fail if unconfigured URLs exist?
> **[COMMENT]**: see above
---

## 12. Success Metrics

The specification will be considered successful when:

1. **URL Discovery:** All non-excluded Django URLs are discovered and categorized
2. **Configuration Coverage:** 95%+ of URLs are configured (not orphaned) **[COMMENT: I plan to have ALL URLs configured, as last reosrt as unassigned or ignored]**
3. **Test Automation:** URL access tests run in CI/CD without manual intervention
4. **Maintenance:** Adding new URL requires only YAML update (no test code changes) **[COMMENT: this is crucial. If i don't change confgig i will get error ("orphend") so i will be forced to assigne them to some group (or assign to "unassigned" as a fallback)]**:
5. **Reporting:** Clear reports on unconfigured URLs and test failures
6. **Performance:** Full test suite completes in <60 seconds

---

## 13. Next Steps

1. **Review this specification** with stakeholders
2. **Answer open questions** (section 11)
3. **Approve architecture** and API design
4. **Begin Phase 1 implementation** (discovery & categorization)
5. **Iterate** based on real-world usage

---

## 14. Appendix: Technical References

### 14.1 Django URL Resolution

```python
from django.urls import get_resolver, URLPattern, URLResolver

resolver = get_resolver()
for pattern in resolver.url_patterns:
    if isinstance(pattern, URLPattern):
        # Terminal URL pattern
        name = pattern.name
        path = str(pattern.pattern)
        callback = pattern.callback
    elif isinstance(pattern, URLResolver):
        # Nested resolver (namespace)
        namespace = pattern.namespace
        nested_patterns = pattern.url_patterns
```

### 14.2 Capability System Integration

```python
from contest.permissions.capabilities import Capability

# Get capability class dynamically
cap_class_path = "contest.permissions.capabilities.Capability"
module_path, class_name = cap_class_path.rsplit(".", 1)
module = __import__(module_path, fromlist=[class_name])
Capability = getattr(module, class_name)

# Get all capabilities
all_caps = [c.name for c in Capability]
```

### 14.3 Permission Checking in Views

```python
# From mixins.py
class CapabilityRequiredMixin:
    required_capability: Capability | None = None
    
    def dispatch(self, request, *args, **kwargs):
        if not request.perm.can(self.required_capability, request.contest):
            return redirect("contest:contest_detail", request.contest.slug)
```

### 14.4 HTTP Client for Testing
> **[COMMENT]**: i Use TestCase class from django.test and built in client
```python
from django.test import Client

client = Client()

# Anonymous request
response = client.get("/contest/entry/create/")

# Logged-in request
client.force_login(user)
response = client.get("/contest/entry/create/")

# Check response
assert response.status_code == 200
assert response.redirect_chain == [("/accounts/login/", 302)]
```

---

**End of Specification**
