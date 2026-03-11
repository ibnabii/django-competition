import contest.views.contest as views
from django.urls import path

urlpatterns = [
    path(
        "details/<slug:contest_slug>/",
        views.ContestDetailView.as_view(),
        name="contest_detail",
    ),
    path(
        "details/<slug:contest_slug>/rules/",
        views.ContestRulesView.as_view(),
        name="contest_rules",
    ),
    path(
        "details/<slug:contest_slug>/addr/",
        views.ContestDeliveryAddressView.as_view(),
        name="contest_address",
    ),
]
