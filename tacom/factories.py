import random

import factory
from django.conf import settings
from faker import Faker

_faker_cache = {}
LOCALES = getattr(settings, "TESTING_LOCALES", ["pl_PL"])


class RandomLocaleDjangoModelFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    _locale = factory.LazyFunction(lambda: random.choice(LOCALES))

    @factory.lazy_attribute
    def _faker(self):
        locale = self._locale if hasattr(self, "_locale") else "pl_PL"
        if locale not in _faker_cache:
            _faker_cache[locale] = Faker(locale)
        return _faker_cache[locale]
