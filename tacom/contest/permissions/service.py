from django.utils.functional import cached_property

from .capabilities import CAPABILITIES, Capability
from .roles import (
    GLOBAL_ROLE_CAPABILITIES,
    CONTEST_ROLE_CAPABILITIES,
    GLOBAL_ROLE_NAMES,
    Role,
)
from contest.models import Contest
from contest.models.membership import ContestMembershipRole


class PermissionService:
    """
    Resolves user capabilities from contest memberships and global roles.
    """

    def __init__(self, user):
        self.user = user

    # --------------------
    # GLOBAL ROLES (via Django groups)
    # --------------------

    @cached_property
    def global_roles(self):
        """
        Returns only the Django groups that are mapped as global roles.
        Ignores unrelated groups.
        """
        if not self.user.is_authenticated:
            return set()
        user_groups = set(self.user.groups.values_list("name", flat=True))
        return user_groups & set(GLOBAL_ROLE_NAMES)

    @cached_property
    def global_capabilities(self):
        caps = set()

        for role in self.global_roles:
            caps |= GLOBAL_ROLE_CAPABILITIES.get(Role(role), set())

        return caps

    # --------------------
    # CONTEST ROLES
    # --------------------

    @cached_property
    def contest_roles_map(self):
        """
        Returns a dict mapping contest_id -> set of Role enums
        """
        if not self.user.is_authenticated:
            return {}

        roles = ContestMembershipRole.objects.filter(
            membership__user=self.user
        ).select_related("membership__contest")

        mapping = {}
        for r in roles:
            contest_id = r.membership.contest_id
            mapping.setdefault(contest_id, set()).add(r.role)

        return mapping

    def contest_capabilities(self, contest: Contest):
        if not contest:
            return set()
        roles = self.contest_roles_map.get(contest.id, set())
        caps = set()
        for role in roles:
            caps |= CONTEST_ROLE_CAPABILITIES.get(Role(role), set())
        return caps

    # --------------------
    # PUBLIC API
    # --------------------

    def can(self, capability: Capability, contest: Contest = None) -> bool:
        """
        Returns True if the user has the given capability in the given contest (or globally)
        """
        meta = CAPABILITIES[capability]
        if meta["scope"] == "global":
            return capability in self.global_capabilities

        if meta["scope"] == "contest":
            if not contest:
                return False
            return capability in self.contest_capabilities(contest)

        return False

    def can_any_contest(self, capability: Capability) -> bool:
        """
        Returns True if the user has the capability in any contest.
        Useful for navbar links that lead to contest selection page.
        """
        meta = CAPABILITIES[capability]

        if meta["scope"] == "global":
            return capability in self.global_capabilities
        for contest_id in self.contest_roles_map:
            roles = self.contest_roles_map[contest_id]
            for role in roles:
                if capability in CONTEST_ROLE_CAPABILITIES.get(Role(role), set()):
                    return True

        return False
