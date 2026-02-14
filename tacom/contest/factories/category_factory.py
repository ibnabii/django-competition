import random

import factory

from contest.models import Category


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    contest = factory.SubFactory("contest.factories.contest_factory.ContestFactory")
    entries_limit = random.randint(1, 10)
    style = factory.SubFactory("contest.factories.style_factory.StyleFactory")
