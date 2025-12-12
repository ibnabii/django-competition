from django.urls import path
import contest.views.general as views

urlpatterns = [
    path("", views.PublishedContestListView.as_view(), name="contest_list"),
]
