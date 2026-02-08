from typing import cast

from capabilities import Capability
from contest.permissions.request_types import AppRequest
from django.core.exceptions import PermissionDenied
from django.views import View


class CapabilityRequiredMixin:
    """
    CBV mixin to enforce capability-based access.
    """

    required_capability: Capability | None = None

    def dispatch(self, request: AppRequest, *args, **kwargs):
        contest = request.contest

        if not self.required_capability:
            raise ValueError("required_capability must be set on the view")

        if not request.perm.can(self.required_capability, contest):
            raise PermissionDenied()

        return cast(View, super()).dispatch(request, *args, **kwargs)
