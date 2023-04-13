from django.views.generic import DetailView
from django.urls import path

from . import views
from .models import Contest

app_name = 'contest'

urlpatterns = [
    path('', views.ContestListView.as_view(), name='contest_list'),
    path('details/<slug:slug>/', DetailView.as_view(
        model=Contest
        ),
        name='contest_detail'),
]