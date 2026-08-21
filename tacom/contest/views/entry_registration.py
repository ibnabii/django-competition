from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView

from contest import payu
from contest.models import Category, Contest, Entry
from contest.views import UserFullProfileMixin, ContestContextMixin
from contest.mixins import NextUrlMixin
from contest.views.contest import ContestAcceptsRegistration


class AddEntryContestListView(LoginRequiredMixin, ListView):
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


class MyEntriesContestView(
    UserFullProfileMixin, ContestContextMixin, NextUrlMixin, ListView
):
    """
    Base view for displaying user's entries in a contest
    """

    context_object_name = "entries"

    def get_queryset(self):
        return (
            Entry.objects.filter(brewer=self.request.user)
            .filter(category__contest=self.contest)
            .select_related("category", "category__style")
            .order_by("category__style__name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.contest.is_registrable:
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
            context["categories"] = (
                Category.objects.not_full(self.request.user)
                .filter(contest=self.contest)
                .select_related("style")
                .order_by("style__name")
            )
        return context


class MyEntriesContestStandaloneView(MyEntriesContestView):
    """
    Standalone page for displaying user's entries in a contest - rendered in one contest context
    """

    template_name = "contest/entry_registration/user_contest_entry_mgmt_page.html"


class MyEntriesContestEmbeddedView(MyEntriesContestView):
    """
    Nested details of user's entries in a contest - rendered when showing multiple contests in one page
    """

    template_name = "contest/entry_registration/_user_contest_entry_mgmt.html"


class MyEntriesView(LoginRequiredMixin, ListView):
    """
    Allows selection of the contest, which user wants to register
    """

    ordering = ["-registration_date_to"]
    queryset = Contest.registrable
    context_object_name = "registrable_contests"
    template_name = "contest/entry_registration/user_entry_mgmt_page.html"

    def dispatch(self, request, *args, **kwargs):
        # redirect straight to only contests page if that's the case
        if Contest.published.count() == 1:
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
                        "contest:add_entry_contest",
                        args=(Contest.published.first().slug,),
                    )
                )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # find all contests, where user has registered
        context["user_contests"] = Contest.published.filter(
            categories__entries__brewer=self.request.user
        ).distinct()
        return context
