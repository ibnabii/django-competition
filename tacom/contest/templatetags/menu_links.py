# templatetags/menu_links.py
from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def contest_url(context, functionality):
    """
    Returns the URL for a given functionality:
    - If contest context exists -> direct contest URL
    - Otherwise -> generic disambiguation URL
    """
    request = context["request"]
    contest = getattr(request, "contest", None)

    if contest:
        # Assume get_functionality_url returns full URL for the functionality
        return reverse(f"contest:{functionality}", args=[contest.slug])
    else:
        # Disambiguation view
        return reverse("contest:disambiguation", args=[functionality])
