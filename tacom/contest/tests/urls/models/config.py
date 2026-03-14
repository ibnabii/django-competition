from datetime import datetime
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
    access_rules: list[AccessRule] | None = None
    no_access_rules: list[AccessRule] | None = None


class DefaultRules(BaseModel):
    access_rules: list[AccessRule] = [AccessRule(any_success=True)]
    no_access_rules: list[AccessRule] | None = None


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
    db_path: str | None = None
    cleanup_on_start: bool = False
    soft_response_time_ms: int = 500


class Config(BaseModel):
    model_config = {"extra": "forbid", "str_strip_whitespace": True}

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
        values = info.data
        cap_class_path = values.get("capability_class")
        if not cap_class_path:
            return v

        module_path, class_name = cap_class_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        capability_class = getattr(module, class_name)

        allowed_caps = {c.name for c in capability_class}
        unknown = set(v.keys()) - allowed_caps
        if unknown:
            raise ValueError(f"Unknown capabilities: {unknown}")
        return v


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class DiscoveredUrl(BaseModel):
    name: str
    namespace: str = ""
    url_pattern: str
    view_module: str
    view_name: str
    supported_methods: list[HttpMethod]

    @property
    def full_name(self) -> str:
        return f"{self.namespace}:{self.name}" if self.namespace else self.name

    @property
    def has_parameters(self) -> bool:
        return "<" in self.url_pattern


class VisitRecord(BaseModel):
    url_full_name: str
    method: HttpMethod
    user_type: str
    status_code: int
    response_time_ms: float
    followed_redirects: bool
    redirect_chain: list[str] = []
    timestamp: datetime
