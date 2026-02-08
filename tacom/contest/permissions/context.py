from .service import PermissionService


class PermissionContext:
    """
    Request-level wrapper for checking capabilities.
    """

    def __init__(self, user):
        self.service = PermissionService(user)

    def can(self, capability, contest=None):
        return self.service.can(capability, contest)

    def can_any_contest(self, capability):
        return self.service.can_any_contest(capability)
