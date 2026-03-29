from django.urls import path
import contest.views.encoding as views


url_patterns = [
    path(
        "codes/<slug:contest_slug>/",
        views.EntriesListView.as_view(),
        name="codes_list",
    ),
    path(
        "codes/<slug:contest_slug>/print/",
        views.EntriesListViewPrintable.as_view(),
        name="codes_list_print",
    ),
    path(
        "codes/<slug:contest_slug>/<uuid:entry_id>/",
        views.EntryNewCodeView.as_view(),
        name="codes_item",
    ),
]
