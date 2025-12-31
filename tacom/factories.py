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
    def faker(self):
        locale = self._locale if hasattr(self, "_locale") else "pl_PL"
        if locale not in _faker_cache:
            _faker_cache[locale] = Faker(locale)
        return _faker_cache[locale]

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Factory Boy classes do not inherit _meta.exclude, hence this override.
        It ensures Factory level attributes are not passed to the model.
        """
        exclude = ("faker", "_locale")
        for item in exclude:
            kwargs.pop(item, None)
        return super()._create(model_class, *args, **kwargs)
