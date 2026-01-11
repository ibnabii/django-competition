from datetime import date
from random import choices
from string import ascii_uppercase, digits

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.db.utils import OperationalError
from django.template.loader import get_template
from django.urls import reverse
from django.utils import translation


def open_contests():
    from .models import Contest

    return (
        Contest.objects.filter(competition_is_published=True)
        .filter(registration_date_from__lte=date.today())
        .filter(registration_date_to__gte=date.today())
    )


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def mail_entry_status_change(entries, new_status):
    template = {
        "PAID": "entries_paid",
        "RECEIVED": "entries_received",
    }
    old_language = translation.get_language()

    if new_status not in template.keys():
        raise ValueError(
            f"mail_entry_status_change: no template defined for status: {new_status}."
        )
    template_txt = get_template("contest/email/" + template.get(new_status) + ".txt")
    template_html = get_template("contest/email/" + template.get(new_status) + ".html")

    user = entries[0].brewer
    translation.activate(user.language)
    contest = entries[0].category.contest
    context = {
        "username": user.first_name,
        "new_status": new_status,
        "entries": entries,
        "contest": contest.title,
        "link": settings.DEFAULT_DOMAIN
        + reverse("contest:add_entry_contest", args=(contest.slug,)),
    }
    subject = "KMP Bartnik - status change"
    from_email = "KMP Bartnik <KMP.Bartnik@gmail.com>"
    to = user.email
    text_content = template_txt.render(context)
    html_content = template_html.render(context)
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
    msg.attach_alternative(html_content, "text/html")
    msg.send()

    translation.activate(old_language)


def code_generator():
    from contest.models import Entry

    # for migration only:
    # return 0
    try:
        maximum_code = Entry.objects.aggregate(models.Max("code"))["code__max"]
    except OperationalError:
        maximum_code = 1000
    if maximum_code:
        return int(maximum_code) + 1
    return 1000


def rebate_code_generator():
    from contest.models import RebateCode

    """Generate a unique 10-character alphanumeric code (uppercase letters and digits)."""
    while True:
        code = "".join(choices(ascii_uppercase + digits, k=10))
        if not RebateCode.objects.filter(code=code).exists():
            return code
