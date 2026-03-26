import contest.views.access_management as views
from django.urls import path

urlpatterns = [
    # Capability switch
    path(
        "<slug:contest_slug>/<int:user_id>/<str:role_name>/toggle",
        views.ToggleContestRoleView.as_view(),
        name="toggle_contest_role",
    ),
    path(
        "<slug:contest_slug>/manage_team/",
        views.ManageTeamPageView.as_view(),
        name="manage_team",
    ),
    path(
        "<slug:contest_slug>/user-search/",
        views.UserSearchView.as_view(),
        name="user_search",
    ),
    path(
        "<slug:contest_slug>/user-add/",
        views.UserAddView.as_view(),
        name="user_add",
    ),
]
