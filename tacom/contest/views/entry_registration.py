from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import ListView

from contest import payu
from contest.models import Contest, Category, Entry
from contest.views import UserFullProfileMixin
from contest.views.contest import ContestAcceptsRegistration


class AddEntryContestListView(ListView):
    """
    Allows selection of the contest, which user wants to register
    """

    ordering = ["-registration_date_to"]
    queryset = Contest.registrable

    template_name = "contest/add_entry_contest_list.html"

    def dispatch(self, request, *args, **kwargs):
        # redirect straight to only contests page if that's the case
        if Contest.objects.count() == 1:
            if Contest.registrable.count() == 1:
                return HttpResponseRedirect(
                    reverse(
                        "contest:add_entry_contest",
                        args=(Contest.registrable.first().slug,),
                    )
                )
            else:
                return HttpResponseRedirect(
                    reverse(
                        "contest:user_entry_list",
                        args=(Contest.objects.first().slug,),
                    )
                )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entries"] = Entry.objects.filter(
            brewer=self.request.user
        ).select_related("category__style", "category__contest")
        return context


class AddEntryStyleListView(
    LoginRequiredMixin, UserFullProfileMixin, ContestAcceptsRegistration, ListView
):
    """
    Allows selection of the Style (via Category), to which user wants to register.
    Contest has been already chosen (and is passed via url slug)
    """

    template_name = "contest/add_entry_style_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        payu.update_user_payments_statuses(self.request.user)
        return (
            Category.objects.not_full(self.request.user)
            .filter(contest=self.contest)
            .select_related("style")
            .order_by("style__name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_limit_left = self.contest.user_limit_left(self.request.user)
        contest_limit_left = self.contest.global_limit_left
        context["user_limit_left"] = user_limit_left
        context["contest_limit_left"] = contest_limit_left
        context["can_add"] = (user_limit_left is None or user_limit_left > 0) and (
            contest_limit_left is None or contest_limit_left > 0
        )
        if not context["can_add"]:
            if user_limit_left is not None and user_limit_left <= 0:
                context["limit_exhausted_info"] = _(
                    "You have reached the limit of entries allowed per participant."
                )
            else:
                context["limit_exhausted_info"] = _(
                    "This competition has reached it's entries limit."
                )
        context["entries"] = (
            Entry.objects.filter(brewer=self.request.user)
            .filter(category__contest=self.contest)
            .select_related("category__style", "category__contest")
        )
        return context
