from django.views.generic import DetailView
from django.urls import path

from . import views
from .models import Style

app_name = 'contest'

urlpatterns = [
    path('', views.PublishedContestListView.as_view(), name='contest_list'),
    path('details/<str:slug>/', views.ContestDetailView.as_view(), name='contest_detail'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('style/<str:slug>/', DetailView.as_view(model=Style), name='style_detail'),
    path('entry/add/', views.AddEntryContestListView.as_view(), name='add_entry'),
    path('entry/add/contest/<str:slug>/', views.AddEntryStyleListView.as_view(), name='add_entry_contest'),
    path('entry/add/category/<uuid:pk>/', views.AddEntryView.as_view(), name='add_entry_category'),
    path('entry/edit/<uuid:pk>/', views.EditEntryView.as_view(), name='entry_edit'),
]