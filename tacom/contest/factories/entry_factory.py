import random
from typing import Any

import factory
from decimal import Decimal
from contest.models import Entry
from contest.factories.category_factory import CategoryFactory
from contest.factories.user_factory import UserFactory  # Your custom User factory


class EntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Entry

    # Foreign Keys
    category = factory.SubFactory(CategoryFactory)
    brewer = factory.SubFactory(UserFactory, profile=True)  # default brewer

    # Fields
    name = factory.Faker("word")  # realistic name
    sweetness = factory.LazyFunction(
        lambda: random.choice([choice[0] for choice in Entry.SweetnessLevel.choices])
    )
    carbonation = factory.LazyFunction(
        lambda: random.choice([choice[0] for choice in Entry.CarbonationLevel.choices])
    )
    extra_info = factory.Faker("sentence", nb_words=12)
    alcohol_content = factory.LazyFunction(
        lambda: Decimal(f"{random.uniform(0, 12):.2f}")
    )

    def __new__(cls, *args: Any, **kwargs: Any) -> Entry:
        return super().__new__(cls)(*args, **kwargs)
