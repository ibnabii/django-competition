import contest.views.entry_registration as views
from django.urls import path

url_patterns = [
    # path("entry/add/", views.AddEntryContestListView.as_view(), name="add_entry"),
    # path(
    #     "entry/add/contest/<slug:contest_slug>/",
    #     views.AddEntryStyleListView.as_view(),
    #     name="add_entry_contest",
    # ),
    path(
        "myentries/contest/<slug:contest_slug>/",
        views.MyEntriesContestStandaloneView.as_view(),
        name="add_entry_contest",
    ),
    path(
        "myentries/contest/<slug:contest_slug>/embedded/",
        views.MyEntriesContestEmbeddedView.as_view(),
        name="add_entry_contest_embedded",
    ),
    path("myentries/", views.MyEntriesView.as_view(), name="add_entry"),
]
