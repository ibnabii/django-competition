from django import template
from django.conf import settings
from contest.permissions.capabilities import Capability, CONTEST_CAPABILITIES
from contest.permissions.request_types import AppRequest

register = template.Library()


@register.simple_tag(takes_context=True)
def can(context, capability_name):
    """
    Usage:
        {% if can "ENTRY_RECEIVE" %}
    """

    request = context.get("request")

    if not request:
        return False

    # Convert string → enum
    try:
        capability = Capability[capability_name]
    except KeyError:
        if settings.DEBUG:
            raise ValueError(f"Unknown capability '{capability_name}'")
        else:
            return False  # or raise error if you prefer strict behaviour

    contest = getattr(request, "contest", None)

    return request.perm.can(capability, contest)


@register.simple_tag(takes_context=True)
def can_any(context):
    request: AppRequest = context.get("request")
    if not request:
        return False

    contest = getattr(request, "contest", None)

    for capability in CONTEST_CAPABILITIES:
        # print(name)
        # try:
        #     capability = Capability[name]
        # except KeyError:
        #     continue

        if request.perm.can(capability, contest):
            # if request.perm.can_any_contest(capability):
            return True

    return False


@register.simple_tag(takes_context=True)
def can_any_contest(context, capability_name):
    request: AppRequest = context.get("request")
    if not request:
        return False

    # Convert string → enum
    try:
        capability = Capability[capability_name]
    except KeyError:
        if settings.DEBUG:
            raise ValueError(f"Unknown capability '{capability_name}'")
        else:
            return False  # or raise error if you prefer strict behaviour
    print(capability)
    return request.perm.can_any_contest(capability)
