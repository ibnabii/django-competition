from datetime import date

from django.db import models


class StyleManager(models.Manager):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class ContestManager(models.Manager):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class PublishedContestManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(competition_is_published=True)


class RegistrableContestManager(models.Manager):
    def get_queryset(self):
        return(super().get_queryset()
               .filter(competition_is_published=True)
               .filter(registration_date_from__lte=date.today())
               .filter(registration_date_to__gte=date.today())
               )


class CategoryManager(models.Manager):
    def full(self, user):
        return (super().get_queryset()
                .filter(entries__brewer=user)
                .prefetch_related('entries')
                .annotate(entries_count=models.Count('entries'))
                .filter(entries_count__gte=models.F('entries_limit'))
                )

    def not_full(self, user):
        return (super().get_queryset()
                .filter(models.Q(entries__brewer=user) | models.Q(entries__isnull=True))
                .prefetch_related('entries')
                .annotate(entries_count=models.Count('entries'))
                .filter(entries_count__lt=models.F('entries_limit'))
                # |
                # super().get_queryset().filter(entries)
                )

