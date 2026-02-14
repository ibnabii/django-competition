from typing import Any

import factory
from contest.models import Style


class StyleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Style

    name = factory.Sequence(lambda n: f"Style {n}")
    description = factory.Sequence(lambda n: f"Style description {n}")
    description_pl = factory.Sequence(lambda n: f"Style description pl {n}")

    def __new__(cls, *args: Any, **kwargs: Any) -> Style:
        return super().__new__(cls)(*args, **kwargs)
