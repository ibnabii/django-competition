from django.shortcuts import get_object_or_404

from contest.models import Contest


class ContestMiddleware:
    """
    Adds request.contest if 'contest_slug' is present in URL.
    """

    contest_slug = "slug"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Called after URL resolution, so we can access view_kwargs directly.
        """
        request.contest = None

        slug = view_kwargs.get(self.contest_slug)

        if slug:
            request.contest = get_object_or_404(Contest, slug=slug)
        return None
