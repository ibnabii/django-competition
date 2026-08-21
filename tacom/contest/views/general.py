from contest.models import Contest
from django.shortcuts import redirect
from django.views.generic import ListView


class PublishedContestListView(ListView):
    ordering = ["-judging_date_from"]
    queryset = Contest.published
    template_name = "contest/general/contest_list.html"

    def get(self, *args, **kwargs):
        contests = self.get_queryset()
        if len(contests) == 1:
            return redirect(
                "contest:contest_detail", contest_slug=self.queryset.first().slug
            )
        self.object_list = contests
        return self.render_to_response(self.get_context_data())


# TODO: delete disambiguation
class DisambiguationView(ListView):
    # queryset = Contest.published
    #
    # def get(self, *args, **kwargs):
    #     functionality = kwargs["functionality"]
    #
    #     # TODO: remove
    #     print("DisambiguationView: ", functionality)
    #
    #     try:
    #         if self.queryset.count() == 1:
    #             return redirect(
    #                 "contest:contest_detail", slug=self.queryset.first().slug
    #             )
    #
    #         return redirect(f"contest:{functionality}", Contest.objects.get(id=17).slug)
    #     except NoReverseMatch:
    #         raise Http404()
    pass
