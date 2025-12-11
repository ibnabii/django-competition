from datetime import date

from django.db import models
from django.db.models import Q
from django.utils import timezone


class StyleManager(models.Manager):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class ContestManager(models.Manager):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class PublishedContestManager(models.Manager):
    def get_queryset(self):
        now = timezone.now()
        return (
            super()
            .get_queryset()
            .filter(
                Q(competition_is_published=True)
                | Q(competition_autopublish_datetime__lte=now)
            )
        )


class RegistrableContestManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(competition_is_published=True)
            .filter(registration_date_from__lte=date.today())
            .filter(registration_date_to__gte=date.today())
        )


class CategoryManager(models.Manager):
    def full(self, user):
        return (
            super()
            .get_queryset()
            .filter(entries__brewer=user)
            .prefetch_related("entries")
            .annotate(entries_count=models.Count("entries"))
            .filter(entries_count__gte=models.F("entries_limit"))
        )

    def not_full(self, user):
        return super().get_queryset().exclude(id__in=self.full(user))


class PaymentManagerExcludeStatuses(models.Manager):

    def __init__(self, statuses, methods=None):
        self.statuses = statuses
        self.methods = methods
        super().__init__()

    def get_queryset(self):
        payments = super().get_queryset().exclude(status__in=self.statuses)
        if self.methods:
            payments = payments.filter(method__code__in=self.methods)
        return payments


class PaymentMethodManager(models.Manager):
    def get_by_natural_key(self, code):
        return self.get(code=code)


class DefaultManager(models.Manager):
    pass
