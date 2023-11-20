from datetime import date

from .models import Contest


def open_contests():
    return (Contest.objects
            .filter(competition_is_published=True)
            .filter(registration_date_from__lte=date.today())
            .filter(registration_date_to__gte=date.today())
            )


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip