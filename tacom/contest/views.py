from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, TemplateView, UpdateView

from django.shortcuts import redirect

from .models import Contest

class ContestListView(ListView):
    model = Contest
    ordering = ['-judging_date_from']
    queryset = Contest.objects.filter(competition_is_published=True)

    def get(self, *args, **kwargs):
        if self.queryset.count() == 1:
            return redirect('contest:contest_detail', slug=self.queryset.first().slug)
        return super(ContestListView, self).get(*args, **kwargs)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'contest/profile.html'
    # user_check_failure_path = reverse_lazy("account_signup")

    def check_user(self, user):
        if user.is_active:
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super(ProfileView, self).get_context_data(**kwargs)
        user = User.objects.get(id=self.request.user.id)
        context['user'] = user
        return context

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
