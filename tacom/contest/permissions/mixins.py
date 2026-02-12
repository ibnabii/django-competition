from typing import cast

from contest.permissions.request_types import AppRequest
from django.shortcuts import redirect
from django.views import View

from .capabilities import Capability


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
            if contest:
                return redirect("contest:contest_detail", contest.slug)
            else:
                return redirect("contest:contest_list")

        return cast(View, super()).dispatch(request, *args, **kwargs)
