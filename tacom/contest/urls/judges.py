import contest.views.judges as views
from django.urls import path

urlpatterns = [
    path(
        "judges/<slug:contest_slug>/",
        views.MainJudgeApplicationView.as_view(),
        name="judge_application",
    ),
    path(
        "judges/<slug:contest_slug>/application/",
        views.JudgeApplicationWidgetView.as_view(),
        name="judge_application_widget",
    ),
    path(
        "judges/<slug:contest_slug>/application/apply/",
        views.JudgeApplicationCreateView.as_view(),
        name="judge_widget_apply",
    ),
    path(
        "judges/<slug:contest_slug>/application/cancel/",
        views.JudgeApplicationCancelView.as_view(),
        name="judge_widget_cancel",
    ),
    path(
        "judge_certification/",
        views.JudgeCertificationDetailView.as_view(),
        name="judge_certification_read",
    ),
    path(
        "judge_certification/edit/",
        views.JudgeCertificationUpdateView.as_view(),
        name="judge_certification_edit",
    ),
]
