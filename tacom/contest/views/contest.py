from contest.models import Category, Contest
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.views.generic import DetailView


class ContestDetailView(DetailView):
    model = Contest
    # queryset = Contest.objects.prefetch_related('categories__style')  # 2 queries
    # queryset = Contest.published.prefetch_related(
    #     #     Prefetch("categories", queryset=Category.objects.select_related("style"))
    #     # )  # 1 query

    # why i have to use get_queryset here becayse adding .prefeech_related executes immediatelly

    def get_queryset(self):
        return Contest.published.prefetch_related(
            Prefetch("categories", queryset=Category.objects.select_related("style"))
        )

    def get_template_names(self):
        """
        based on  htmx header: HX-Request, if "embed" == "true",
        the template used will be only view-specific data,
        otherwise it will extend base.html, to add bars, styling, etc

        """
        if self.request.headers.get("HX-Request") == "true":
            return ["contest/contest/contest_detail.html"]
        else:
            return ["contest/contest/contest_detail_standalone.html"]


class ContestRulesView(DetailView):
    model = Contest
    template_name = "contest/contest/contest_rules.html"


class ContestDeliveryAddressView(DetailView):
    model = Contest
    template_name = "contest/contest/contest_delivery_addr.html"
    queryset = Contest.published


class ContestContextMixin:
    contest_slug_kwarg = "slug"

    @cached_property
    def contest(self) -> Contest:
        slug = self.kwargs.get("slug")
        return get_object_or_404(Contest, slug=slug)
