from datetime import date

from .models import Contest


def open_contests():
    return (Contest.objects
            .filter(competition_is_published=True)
            .filter(registration_date_from__lte=date.today())
            .filter(registration_date_to__gte=date.today())
            )
