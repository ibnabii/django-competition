from django.http import Http404
from django.urls import NoReverseMatch

from contest.models import Contest
from django.shortcuts import redirect
from django.views.generic import ListView


class PublishedContestListView(ListView):
    ordering = ["-judging_date_from"]
    queryset = Contest.published
    template_name = "contest/general/contest_list.html"

    def get(self, *args, **kwargs):
        if self.queryset.count() == 1:
            return redirect("contest:contest_detail", slug=self.queryset.first().slug)
        return super().get(*args, **kwargs)


# TODO: finish disambiguation
class DisambiguationView(ListView):
    queryset = Contest.published

    def get(self, *args, **kwargs):
        functionality = kwargs["functionality"]

        # TODO: remove
        print("DisambiguationView: ", functionality)

        try:
            if self.queryset.count() == 1:
                return redirect(
                    "contest:contest_detail", slug=self.queryset.first().slug
                )

            return redirect(f"contest:{functionality}", Contest.objects.get(id=17).slug)
        except NoReverseMatch:
            raise Http404()
