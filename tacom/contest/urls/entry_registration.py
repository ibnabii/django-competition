from django.urls import path
import contest.views.entry_registration as views

url_patterns = [
    path("entry/add/", views.AddEntryContestListView.as_view(), name="add_entry"),
    path(
        "entry/add/contest/<str:slug>/",
        views.AddEntryStyleListView.as_view(),
        name="add_entry_contest",
    ),
]
