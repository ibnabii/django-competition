from django.views.generic import DetailView
from django.urls import path

from . import views
from .models import Contest, Style

app_name = 'contest'

urlpatterns = [
    path('', views.ContestListView.as_view(), name='contest_list'),
    path('details/<slug:slug>/', views.ContestDetailView.as_view(), name='contest_detail'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('style/<slug:slug>/', DetailView.as_view(model=Style), name='style_detail'),
]