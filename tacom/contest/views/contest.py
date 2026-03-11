import abc
from abc import ABC

from contest.models import Category, Contest
from contest.permissions.request_types import AppRequest
from django.contrib import messages
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic.base import ContextMixin


# TODO: should this be a contxt mixin?
class ContestContextMixin(ContextMixin):
    """
    Ensures self.contest is set
    """

    slug_url_kwarg = "contest_slug"
    kwargs: dict

    @cached_property
    def contest(self) -> Contest:
        slug = self.kwargs.get(self.slug_url_kwarg)
        return get_object_or_404(Contest, slug=slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contest"] = self.contest
        return context


class ContestPassesTestMixin(ContestContextMixin, ABC):
    """
    Ensures contest passes test
    """

    @abc.abstractmethod
    def test_func(self) -> bool: ...

    def dispatch(self, request, *args, **kwargs):
        contest_test_result = self.test_func()
        if not contest_test_result:
            messages.warning(
                request, self.contest.title + " " + _("is not enabled for this")
            )
            previous = request.META.get("HTTP_REFERER")
            if previous and request.path not in previous:
                return redirect(previous)
            else:
                return redirect("contest:contest_detail", slug=self.contest.slug)

        return super().dispatch(request, *args, **kwargs)


class ContestAcceptsRegistration(ContestContextMixin):

    def get(self, request: AppRequest, *args, **kwargs):

        if self.contest.is_registrable:
            return super().get(request, *args, **kwargs)
        else:
            raise Http404


class ContestDetailView(ContestContextMixin, DetailView):
    model = Contest
    # queryset = Contest.objects.prefetch_related('categories__style')  # 2 queries
    # queryset = Contest.published.prefetch_related(
    #     #     Prefetch("categories", queryset=Category.objects.select_related("style"))
    #     # )  # 1 query

    # why I have to use get_queryset here because adding .prefetch_related executes immediately

    def get_queryset(self):
        return Contest.published.prefetch_related(
            Prefetch("categories", queryset=Category.objects.select_related("style"))
        )

    def get_template_names(self):
        """
        based on htmx header: HX-Request, if "embed" == "true",
        the template used will be only view-specific data,
        otherwise it will extend base.html, to add bars, styling, etc.

        """
        if self.request.headers.get("HX-Request") == "true":
            return ["contest/contest/contest_detail.html"]
        else:
            return ["contest/contest/contest_detail_standalone.html"]


class ContestRulesView(ContestContextMixin, DetailView):
    model = Contest
    template_name = "contest/contest/contest_rules.html"


class ContestDeliveryAddressView(ContestContextMixin, DetailView):
    model = Contest
    template_name = "contest/contest/contest_delivery_addr.html"
    queryset = Contest.published
