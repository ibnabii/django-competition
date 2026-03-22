from django.contrib.auth import get_user_model
from django.http import Http404
from django.shortcuts import render, get_object_or_404
from django.views import View

from contest.models.membership import ContestMembership
from contest.permissions.capabilities import Capability
from contest.permissions.mixins import CapabilityRequiredMixin
from contest.permissions.roles import Role
from contest.utils import get_role_state
from contest.views import ContestContextMixin

User = get_user_model()


class ToggleContestRoleView(ContestContextMixin, CapabilityRequiredMixin, View):
    required_capability = Capability.CONTEST_MANAGE_JUDGES
    template_name = "contest/widgets/role_switch.html"
    allowed_roles = [Role.JUDGE, Role.JUDGE_FINALS, Role.JUDGE_BOS]

    def _render_switch(self, request):
        """Common method to render the switch with current value"""
        value = get_role_state(self.user, self.contest, self.role)
        context = {
            "user": self.user,
            "role": self.role,
            "contest_slug": self.contest.slug,
            "value": value,  # True/False for toggle
        }
        return render(request, self.template_name, context)

    def __init__(self, *args, **kwargs):
        self.user: User | None = None
        self.role: Role | None = None
        super().__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Extract once, available in all HTTP methods
        user_id = kwargs.get("user_id")
        role_name = kwargs.get("role_name")
        # Fetch objects
        self.user = get_object_or_404(User, pk=user_id)
        # Convert role string to Role enum
        try:
            self.role = Role(role_name)
        except ValueError:
            raise Http404()
        # Validate role is allowed in view
        if self.role not in self.allowed_roles:
            raise Http404()
        # Continue normal dispatch
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self._render_switch(request)

    def post(self, request, *args, **kwargs):
        enabled = request.POST.get("enabled") == "true"

        # update membership
        ContestMembership.set_role(self.user, self.contest, self.role, enabled)

        # render updated switch
        return self._render_switch(request)
