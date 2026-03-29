from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.views.generic import ListView

from contest.models.membership import ContestMembership
from contest.permissions.capabilities import Capability
from contest.permissions.mixins import CapabilityRequiredMixin
from contest.permissions.request_types import AppRequest
from contest.permissions.roles import Role, LIST_ROLES_JUDGES, LIST_ROLES_TEAM
from contest.utils import get_role_state
from contest.views import ContestContextMixin

User = get_user_model()


class ToggleContestRoleView(ContestContextMixin, CapabilityRequiredMixin, View):
    required_capability = [
        Capability.CONTEST_MANAGE_JUDGES,
        Capability.CONTEST_MANAGE_TEAM,
    ]

    allowed_roles: dict[Capability, list[Role]] = {
        Capability.CONTEST_MANAGE_JUDGES: LIST_ROLES_JUDGES,
        Capability.CONTEST_MANAGE_TEAM: LIST_ROLES_TEAM,
    }

    template_name = "contest/widgets/role_switch.html"

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

    def dispatch(self, request: AppRequest, *args, **kwargs):
        # Extract once, available in all HTTP methods
        user_id = kwargs.get("user_id")
        role_name = kwargs.get("role_name")
        # Convert role string to Role enum
        try:
            self.role = Role(role_name)
        except ValueError:
            raise Http404()

        # Validate role is allowed in view
        if self.role not in {
            role for roles in self.allowed_roles.values() for role in roles
        }:
            raise Http404()

        # Validate user has capability for the given role
        capabilities = [
            capability
            for capability, roles in self.allowed_roles.items()
            if self.role in roles
        ]
        if not any(
            request.perm.can(capability, self.contest) for capability in capabilities
        ):
            raise Http404()

        # Fetch objects
        self.user = get_object_or_404(User, pk=user_id)

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


class ManageTeamPageView(ContestContextMixin, CapabilityRequiredMixin, ListView):
    required_capability = Capability.CONTEST_MANAGE_TEAM
    template_name = "contest/team_management_page.html"
    context_object_name = "memberships"
    model = ContestMembership
    managed_roles = LIST_ROLES_TEAM

    def get_queryset(self):
        return (
            self.model.objects.filter(
                contest=self.contest,
                roles__role__in=[role.value for role in self.managed_roles],
            )
            .distinct()
            .select_related("user")
            .with_roles()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["roles"] = self.managed_roles
        context["role_map"] = {
            membership.user.id: {
                role.value: (role.value in [r.role for r in membership.roles.all()])
                for role in context["roles"]
            }
            for membership in context.get("memberships", [])
        }
        return context


class UserSearchView(ContestContextMixin, CapabilityRequiredMixin, View):
    template_name = "contest/team_management/_team_form_dropdown.html"
    required_capability = Capability.CONTEST_MANAGE_TEAM

    def get(self, request, *args, **kwargs):
        query = request.GET.get("user_search", "").strip()
        users = User.objects.none()

        if query:
            users = (
                User.objects.filter(
                    Q(first_name__icontains=query)
                    | Q(last_name__icontains=query)
                    | Q(email__icontains=query)
                )
                .exclude(contest_memberships__contest=self.contest)
                .order_by("first_name", "last_name")[:10]
            )

        return render(
            request,
            self.template_name,
            {
                "users": users,
                "query": query,
            },
        )


class UserAddView(ContestContextMixin, CapabilityRequiredMixin, View):
    template_name = "contest/team_management/_team_item.html"
    required_capability = Capability.CONTEST_MANAGE_TEAM

    def post(self, request, *args, **kwargs):
        user_id = request.POST.get("user_id")

        if not user_id:
            raise Http404()

        # check if id is of valid type:
        field = User._meta.pk  # primary key field

        try:
            # Convert using Django's internal logic
            field.to_python(user_id)
        except (ValueError, TypeError, ValidationError):
            raise Http404()

        user = get_object_or_404(User, id=user_id)
        roles = ManageTeamPageView.managed_roles
        m = ContestMembership(user=user, contest=self.contest)
        return render(
            request,
            self.template_name,
            {
                "m": m,
                "contest": self.contest,
                "roles": roles,
                "role_map": {user.id: {role.value: False for role in roles}},
            },
        )
