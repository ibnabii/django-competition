from django.views.generic import ListView
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