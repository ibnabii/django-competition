import contest.views.judges as views
from django.urls import path

urlpatterns = [
    path(
        "judges/<str:slug>/",
        views.MainJudgeApplicationView.as_view(),
        name="judge_application",
    ),
    path(
        "judges/<str:slug>/application/",
        views.JudgeApplicationWidgetView.as_view(),
        name="judge_application_widget",
    ),
    path(
        "judges/<str:slug>/application/apply/",
        views.JudgeApplicationCreateView.as_view(),
        name="judge_widget_apply",
    ),
    path(
        "judges/<str:slug>/application/cancel/",
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
