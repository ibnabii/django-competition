from typing import cast

from contest.permissions.request_types import AppRequest
from django.shortcuts import redirect
from django.views import View

from .capabilities import Capability


class CapabilityRequiredMixin:
    """
    CBV mixin to enforce capability-based access.
    """

    required_capability: Capability | list[Capability] | None = None

    def dispatch(self, request: AppRequest, *args, **kwargs):
        contest = request.contest
        if not self.required_capability:
            raise ValueError("required_capability must be set on the view")

        if not isinstance(self.required_capability, list):
            self.required_capability = [self.required_capability]

        if not any(
            request.perm.can(capability, contest)
            for capability in self.required_capability
        ):
            if contest:
                return redirect("contest:contest_detail", contest.slug)
            else:
                return redirect("contest:contest_list")

        return cast(View, super()).dispatch(request, *args, **kwargs)
