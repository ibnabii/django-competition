from django.views.generic import DetailView
from django.urls import path

from . import views
from .models import Style

app_name = "contest"

urlpatterns = [
    path("", views.PublishedContestListView.as_view(), name="contest_list"),
    path(
        "details/<str:slug>/", views.ContestDetailView.as_view(), name="contest_detail"
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
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/edit/", views.ProfileEditView.as_view(), name="profile_edit"),
    path("style/<str:slug>/", DetailView.as_view(model=Style), name="style_detail"),
    path("entry/add/", views.AddEntryContestListView.as_view(), name="add_entry"),
    path(
        "entry/add/contest/<str:slug>/",
        views.AddEntryStyleListView.as_view(),
        name="add_entry_contest",
    ),
    path(
        "entry/contest/<str:slug>/",
        views.UsersEntryListView.as_view(),
        name="user_entry_list",
    ),
    path(
        "entry/add/category/<uuid:pk>/",
        views.AddEntryView.as_view(),
        name="add_entry_category",
    ),
    path("entry/edit/<uuid:pk>/", views.EditEntryView.as_view(), name="entry_edit"),
    path(
        "entry/delete/<uuid:pk>/", views.DeleteEntryView.as_view(), name="entry_delete"
    ),
    path(
        "entry/results/<uuid:pk>/",
        views.MyScoreSheetView.as_view(),
        name="entry_results",
    ),
    path(
        "<str:slug>/payment/",
        views.AddPackageForPayment.as_view(),
        name="payment_start",
    ),
    path(
        "<str:slug>/payment/<uuid:package_id>/",
        views.SelectPaymentMethodView.as_view(),
        name="payment_method_selection",
    ),
    path(
        "payment/<uuid:payment_id>/fake/",
        views.FakePaymentView.as_view(),
        name="payment_fake",
    ),
    path(
        "payment/<uuid:payment_id>/transfer/",
        views.TransferPaymentView.as_view(),
        name="payment_transfer",
    ),
    path(
        "payment/<uuid:payment_id>/payu/",
        views.PayUPaymentView.as_view(),
        name="payment_payu",
    ),
    path(
        "payment/payu/<str:contest_slug>/",
        views.PayUPaymentRedirectView.as_view(),
        name="payment_payu_redirect",
    ),
    path(
        "payment/payu/notification/<uuid:payment_id>/",
        views.PayUNotificationView.as_view(),
        name="payment_payu_notification",
    ),
    path(
        "payment/<uuid:payment_id>/paypal/",
        views.PayPalDispatchView.as_view(),
        name="payment_paypal",
    ),
    path(
        "payment/paypal/success/<uuid:payment_id>/",
        views.PayPalSuccessRedirectView.as_view(),
        name="payment_paypal_success",
    ),
    path(
        "payment/paypal/failure/<uuid:payment_id>/",
        views.PayPalFailureRedirectView.as_view(),
        name="payment_paypal_failure",
    ),
    path(
        "<str:slug>/print/", views.AddPackageForPrinting.as_view(), name="labels_start"
    ),
    path(
        "print/<uuid:package_id>/",
        views.LabelPrintoutView.as_view(),
        name="labels_print",
    ),
    path(
        "<str:slug>/mgmt/delivery/",
        views.AddPackageOfDelivered.as_view(),
        name="delivery_select",
    ),
    path(
        "mgmt/delivery/<uuid:pk>/",
        views.ProcessPackageDelivered.as_view(),
        name="delivery_process",
    ),
    path(
        "<str:slug>/mgmt/payments/",
        views.PaymentManagementView.as_view(),
        name="payment_list",
    ),
    path(
        "mgmt/payments/<uuid:pk>/",
        views.PaymentReceivedView.as_view(),
        name="payment_process",
    ),
    path("<str:slug>/judging/", views.JudgingListView.as_view(), name="judging_list"),
    path(
        "scoresheet/<uuid:pk>/", views.ScoreSheetView.as_view(), name="scoresheet_view"
    ),
    path(
        "scoresheet/<uuid:pk>/edit/",
        views.ScoreSheetEdit.as_view(),
        name="scoresheet_edit",
    ),
    path(
        "entry/<uuid:entry>/scoresheet/",
        views.ScoreSheetCreate.as_view(),
        name="scoresheet_create",
    ),
    path(
        "<str:contest_slug>/results/",
        views.MedalsListView.as_view(),
        name="contest_results",
    ),
    path("privacy/", views.PrivacyView.as_view(), name="privacy"),
    path("partners/", views.PartnersGalleryView.as_view(), name="partners_gallery"),
]
