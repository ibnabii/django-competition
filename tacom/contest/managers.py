from django.db import models


class StyleManager(models.Manager):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class ContestManager(models.Manager):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


Style.objects = StyleManager()
Contest.objects = ContestManager()
