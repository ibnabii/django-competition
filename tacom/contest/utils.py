from datetime import date

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.urls import reverse


def open_contests():
    from .models import Contest
    return (Contest.objects
            .filter(competition_is_published=True)
            .filter(registration_date_from__lte=date.today())
            .filter(registration_date_to__gte=date.today())
            )


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    print(x_forwarded_for)
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def mail_entry_status_change(entries, new_status):
    template = {
        'PAID': 'entries_paid'
    }

    if new_status not in template.keys():
        raise ValueError(f'mail_entry_status_change: no template defined for status: {new_status}.')
    template_txt = get_template('contest/email/' + template.get(new_status) + '.txt')
    template_html = get_template('contest/email/' + template.get(new_status) + '.html')

    user = entries[0].brewer
    contest = entries[0].category.contest
    context = {
        'username': user.username,
        'new_status': new_status,
        'entries': entries,
        'contest': contest.title,
        'link': settings.DEFAULT_DOMAIN + reverse('contest:add_entry_contest', args=(contest.slug,))
    }
    subject = 'Polish Mead Masters - status change'
    from_email = 'Polish Mead Masters <polish.mead.masters@gmail.com>'
    to = user.email
    text_content = template_txt.render(context)
    html_content = template_html.render(context)
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
