from dataclasses import dataclass

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import (
    Http404,
    HttpResponseRedirect,
    HttpRequest,
)
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.functional import cached_property, Promise
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView, UpdateView

from contest.models import Contest
from contest.models.judges import JudgeCertification, JudgeInCompetition
from contest.views import UserFullProfileMixin
from contest.views.contest import ContestContextMixin


class JudgesCanRegisterMixin(ContestContextMixin, View):
    """
    Ensure Contest allows judge registration
    """

    def dispatch(self, request, *args, **kwargs):
        # Always run validation
        if not self.contest.can_judges_register:
            raise Http404
        return super().dispatch(request, *args, **kwargs)


class MainJudgeApplicationView(
    JudgesCanRegisterMixin, LoginRequiredMixin, UserFullProfileMixin, TemplateView
):
    template_name = "contest/judges/judge_application.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contest"] = self.contest
        context["application_status"] = self.get_application_status()
        return context

    def get_application_status(self):
        try:
            application = JudgeInCompetition.objects.get(
                user=self.request.user,
                contest=self.contest,
            )
        except JudgeInCompetition.DoesNotExist:
            return None

        return application.status


class JudgeCertificationUpdateView(LoginRequiredMixin, UpdateView):
    model = JudgeCertification
    fields = ["is_mead_bjcp", "is_mjp", "is_other", "mjp_level", "other_description"]
    template_name = "contest/judges/judge_certification_edit.html"
    success_url = reverse_lazy("contest:judge_certification_read")

    def get_object(self, queryset=None):
        # Get existing or create a new instance
        # obj, created = JudgeCertification.objects.get_or_create(user=self.request.user)
        obj = JudgeCertification.objects.filter(user=self.request.user).first()
        return obj

    def form_valid(self, form):
        has_any = any(
            form.cleaned_data.get(field)
            for field in ["is_mead_bjcp", "is_mjp", "is_other"]
        )

        if not has_any:
            if self.object:
                self.object.delete()
            return HttpResponseRedirect(self.success_url)

        form.instance.user = self.request.user
        return super().form_valid(form)


class JudgeCertificationDetailView(LoginRequiredMixin, TemplateView):

    def get(self, request, *args, **kwargs):
        certification = JudgeCertification.objects.filter(
            user=self.request.user
        ).first()

        if certification is None:
            return render(request, "contest/judges/judge_certification_empty.html")
        else:
            return render(
                request,
                "contest/judges/judge_certification_read.html",
                {"object": certification},
            )


class JudgeApplicationContextMixin(ContestContextMixin):
    request: HttpRequest

    @cached_property
    def application(self) -> JudgeInCompetition | None:
        try:
            return JudgeInCompetition.objects.get(
                contest=self.contest, user=self.request.user
            )
        except JudgeInCompetition.DoesNotExist:
            return None

    @cached_property
    def application_status(self) -> JudgeInCompetition.Status | None:
        return self.application.status if self.application else None

    def refresh_application_cache(self):
        for attr in ("application", "application_status"):
            if hasattr(self, attr):
                delattr(self, attr)


class JudgeApplicationWidgetMixin(JudgeApplicationContextMixin):
    template_map = {
        None: "contest/judges/widgets/apply.html",
        JudgeInCompetition.Status.APPLICATION: "contest/judges/widgets/applied.html",
        JudgeInCompetition.Status.APPROVED: "contest/judges/widgets/applied.html",
        JudgeInCompetition.Status.REJECTED: "contest/judges/widgets/rejected.html",
    }

    def render_widget(self, request, *, error: str | None = None):
        template = self.template_map[self.application_status]
        return render(
            request,
            template,
            {
                "contest": self.contest,
                "application": self.application,
                "error": error,
            },
        )


@dataclass(frozen=True)
class PolicyResult:
    allowed: bool
    reason: str | Promise | None = None


class JudgeApplicationPolicyMixin:
    """
    Provides permission/state rules for JudgeInCompetition actions.
    """

    application: JudgeInCompetition | None = None
    application_status: JudgeInCompetition.Status | None = None
    contest: Contest
    request: HttpRequest

    def can_apply(self) -> PolicyResult:
        """
        Returns True if the user can create a new JudgeInCompetition for the contest.
        """
        # Judge has to provide certification
        try:
            self.request.user.judgecertification
        except JudgeCertification.DoesNotExist:
            return PolicyResult(
                False,
                _("You must provide information about your judge certificates first."),
            )

        # No application must exist yet
        if self.application:
            return PolicyResult(False, _("You already applied for judging."))

        return PolicyResult(True)

    def can_withdraw(self) -> PolicyResult:
        """
        Returns True if the user can cancel an existing application.
        Only APPLICATION or APPROVED can be withdrawn.
        """

        # cannot withdraw rejected applications
        if self.application_status == JudgeInCompetition.Status.REJECTED:
            return PolicyResult(False, _("You cannot withdraw a rejected application."))

        if not self.application:
            return PolicyResult(False, _("You have not applied for judging."))

        return PolicyResult(True)

    # def can_view_widget(self) -> bool:
    #     """
    #     Optional: whether user can see the judge widget at all.
    #     Useful if some users (e.g., non-judges) should not see it.
    #     """
    #     return True


class JudgeApplicationWidgetView(
    JudgeApplicationWidgetMixin,
    JudgesCanRegisterMixin,
    View,
):
    def get(self, request, *args, **kwargs):
        return self.render_widget(request)


class JudgeApplicationCreateView(
    JudgeApplicationWidgetMixin,
    JudgesCanRegisterMixin,
    JudgeApplicationPolicyMixin,
    View,
):
    def post(self, request, *args, **kwargs):
        decision = self.can_apply()
        if not decision.allowed:
            return self.render_widget(request, error=decision.reason)

        JudgeInCompetition.objects.get_or_create(
            contest=self.contest, user=request.user
        )
        self.refresh_application_cache()
        return self.render_widget(request)


class JudgeApplicationCancelView(
    JudgeApplicationWidgetMixin, JudgeApplicationPolicyMixin, View
):
    def post(self, request, *args, **kwargs):
        decision = self.can_withdraw()
        if not decision.allowed:
            return self.render_widget(request, error=decision.reason)

        self.application.delete()
        self.refresh_application_cache()
        return self.render_widget(request)
