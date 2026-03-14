from pydantic import BaseModel, field_validator


class ExcludeConfig(BaseModel):
    apps: list[str] = []
    names: list[str] = []
    modules: list[str] = []


class RoutePack(BaseModel):
    names: list[str]
    name_space: str = ""


class AccessRule(BaseModel):
    # any success is enough even if that code is not on status_codes list
    any_success: bool = False

    # list of status codes that are considered as success when not redirecting,
    # if 302 is allowed, test also with following redirects
    status_codes: list[int] = []

    # if not empty, then following redirects page may end up with success (usually 200: OK) on one of the targets
    # and still be considered as no access.
    allowed_redirect_targets: list[RoutePack] = []


class RoutePolicy(BaseModel):
    routes: list[RoutePack]
    access_rules: list[AccessRule] = [AccessRule(any_success=True)]
    no_access_rules: list[AccessRule] = [
        AccessRule(
            status_codes=[
                401,
                403,
                404,
            ]
        )
    ]


class Config(BaseModel):
    class Config:
        extra = "forbid"  # forbid extra fields
        str_strip_whitespace = True  # optional: strip strings

    exclude: ExcludeConfig
    anonymous: list[RoutePolicy] = []  # pages that can be accessed without login
    logged_in: list[RoutePolicy] = []  # pages that can be accessed only after login
    unassigned: list[RoutePack] = []  # pages that will be configured later

    # e.g., "contest.permissions.capabilities.Capability"
    capability_class: str | None = None
    by_capability: dict[str, list[RoutePolicy]] = {}
    by_group: dict[str, list[RoutePolicy]] = {}

    @field_validator("by_capability", mode="before")
    @classmethod
    def validate_by_capability(cls, v, info):
        """
        Validate that all keys in by_capability exist in the capability_class Enum.
        Only runs if capability_class is provided.
        """
        values = info.data  # dict of already-set fields
        cap_class_path = values.get("capability_class")
        if not cap_class_path:
            # capability_class not provided → skip validation
            return v

        # dynamic import
        module_path, class_name = cap_class_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        capability_class = getattr(module, class_name)

        # validate keys
        allowed_caps = {c.name for c in capability_class}
        unknown = set(v.keys()) - allowed_caps
        if unknown:
            raise ValueError(f"Unknown capabilities: {unknown}")
        return v
