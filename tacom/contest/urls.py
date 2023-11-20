from django.views.generic import DetailView
from django.urls import path

from . import views
from .models import Style

app_name = 'contest'

urlpatterns = [
    path('', views.PublishedContestListView.as_view(), name='contest_list'),
    path('details/<str:slug>/', views.ContestDetailView.as_view(), name='contest_detail'),
    path('details/<str:slug>/addr', views.ContestDeliveryAddressView.as_view(), name='contest_address'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('style/<str:slug>/', DetailView.as_view(model=Style), name='style_detail'),
    path('entry/add/', views.AddEntryContestListView.as_view(), name='add_entry'),
    path('entry/add/contest/<str:slug>/', views.AddEntryStyleListView.as_view(), name='add_entry_contest'),
    path('entry/add/category/<uuid:pk>/', views.AddEntryView.as_view(), name='add_entry_category'),
    path('entry/edit/<uuid:pk>/', views.EditEntryView.as_view(), name='entry_edit'),
    path('entry/delete/<uuid:pk>/', views.DeleteEntryView.as_view(), name='entry_delete'),
    path('<str:slug>/payment', views.AddPackageForPayment.as_view(), name='payment_start'),
    path('<str:slug>/payment/<uuid:package_id>',
         views.SelectPaymentMethodView.as_view(),
         name='payment_method_selection'),
    path('payment/<uuid:payment_id>/fake/', views.FakePaymentView.as_view(), name='payment_fake'),
    path('payment/<uuid:payment_id>/transfer/', views.TransferPaymentView.as_view(), name='payment_transfer'),
    path('payment/<uuid:payment_id>/payu/', views.PayUPaymentView.as_view(), name='payment_payu'),
    path('payment/payu/<str:contest_slug>/', views.PayUPaymentRedirectView.as_view(), name='payment_payu_redirect'),
    path('payment/payu/notification/<uuid:payment_id>/',
         views.PayUNotificationView.as_view(),
         name='payment_payu_notification'),
]