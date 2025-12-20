import contest.views.general as views
from django.urls import path

urlpatterns = [
    path("", views.PublishedContestListView.as_view(), name="contest_list"),
]
