import random
from typing import TYPE_CHECKING, Any

import factory

from contest.models import Category


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    contest = factory.SubFactory("contest.factories.contest_factory.ContestFactory")
    entries_limit = random.randint(1, 10)
    style = factory.SubFactory("contest.factories.style_factory.StyleFactory")

    if TYPE_CHECKING:

        def __call__(self, *args: Any, **kwargs: Any) -> Category: ...
        @classmethod
        def create(cls, **kwargs: Any) -> Category: ...
        @classmethod
        def build(cls, **kwargs: Any) -> Category: ...
