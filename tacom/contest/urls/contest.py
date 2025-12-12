from django.urls import path
import contest.views.contest as views

urlpatterns = [
    path(
        "details/<str:slug>/",
        views.ContestDetailView.as_view(),
        name="contest_detail",
    ),
    path(
        "details/<str:slug>/rules/",
        views.ContestRulesView.as_view(),
        name="contest_rules",
    ),
    path(
        "details/<str:slug>/addr/",
        views.ContestDeliveryAddressView.as_view(),
        name="contest_address",
    ),
]
