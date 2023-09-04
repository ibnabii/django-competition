from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.urls import reverse_lazy
from django.views.generic import ListView, TemplateView, UpdateView, DetailView

from django.shortcuts import redirect

from .models import Contest, Category


class ContestListView(ListView):
    model = Contest
    ordering = ['-judging_date_from']
    queryset = Contest.objects.filter(competition_is_published=True)

    def get(self, *args, **kwargs):
        if self.queryset.count() == 1:
            return redirect('contest:contest_detail', slug=self.queryset.first().slug)
        return super(ContestListView, self).get(*args, **kwargs)


class ContestDetailView(DetailView):
    model = Contest
    # queryset = Contest.objects.prefetch_related('categories__style')  # 2 queries
    queryset = Contest.objects.prefetch_related(
        Prefetch('categories', queryset=Category.objects.select_related('style'))
    )  # 1 query


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'contest/profile.html'


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = 'contest/generic_update.html'
    fields = [
        'username',
        'first_name',
        'last_name',
    ]
    success_url = reverse_lazy('contest:profile')

    def get_object(self, queryset=None):
        return self.request.user
