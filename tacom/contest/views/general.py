from django.shortcuts import redirect
from django.views.generic import ListView

from contest.models import Contest


class PublishedContestListView(ListView):
    ordering = ["-judging_date_from"]
    queryset = Contest.published
    template_name = "contest/general/contest_list.html"

    def get(self, *args, **kwargs):
        if self.queryset.count() == 1:
            return redirect("contest:contest_detail", slug=self.queryset.first().slug)
        return super().get(*args, **kwargs)
