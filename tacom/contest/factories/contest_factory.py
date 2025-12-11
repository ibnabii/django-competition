import random
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import factory
from contest.models import Contest
from django.utils import timezone
from factories import RandomLocaleDjangoModelFactory
from pydantic import BaseModel


def make_contest(*args, **kwargs) -> Contest:
    return ContestFactory(*args, **kwargs)


class PeriodState(str, Enum):
    before = "before"
    during = "during"
    after = "after"


class ContestState(BaseModel):
    registration: PeriodState = PeriodState.during
    delivery: PeriodState = PeriodState.during
    judging: PeriodState = PeriodState.during

    competition_is_published: bool = True
    result_is_published: bool = True

    competition_autopublish_datetime: datetime | None = None
    result_autopublish_datetime: datetime | None = None

    is_judging_eliminations: bool = True
    is_judging_finals: bool = True
    is_judging_bos: bool = True


class ContestFactory(RandomLocaleDjangoModelFactory):
    class Meta:
        model = Contest
        # exclude factory only attributes from passing to model
        exclude = ("_state", "_faker", "_locale")

    title = factory.LazyAttribute(lambda o: o._faker.sentence(nb_words=5))
    # slug = factory.LazyAttribute(lambda o: o._faker.slug())
    description = factory.Faker(locale="en_US", provider="paragraph", nb_sentences=15)
    description_pl = factory.Faker(
        locale="pl_PL", provider="paragraph", nb_sentences=15
    )
    rules = factory.Faker(locale="en_US", provider="paragraph", nb_sentences=15)
    rules_pl = factory.Faker(locale="pl_PL", provider="paragraph", nb_sentences=15)
    logo = None
    entry_fee_amount = factory.Faker(
        "pydecimal", left_digits=2, right_digits=2, positive=True
    )
    entry_fee_currency = factory.LazyFunction(
        lambda: random.choice(["PLN", "EUR", "USD", "SEK"])
    )
    payment_transfer_info = factory.LazyAttribute(
        lambda o: "\n".join((o._faker.name(), o._faker.address(), o._faker.iban()))
    )
    discount_rate = 10
    entry_global_limit = None
    entry_user_limit = None
    delivery_address = factory.LazyAttribute(
        lambda o: "\n".join(
            (o._faker.company(), o._faker.address(), o._faker.phone_number())
        )
    )
    # --- Contest state input ---
    # _state: ContestState = ContestState()  # Default: all 'during'
    _state = factory.LazyFunction(ContestState)

    # --- Logic for date periods based on 'state' ---
    @factory.lazy_attribute
    def registration_date_from(self):
        now = timezone.now().date()
        mode = self._state.registration
        if mode == PeriodState.before:  # In future
            return now + timedelta(days=5)
        elif mode == PeriodState.after:
            return now - timedelta(days=20)
        else:  # mode == PeriodState.during:
            return now - timedelta(days=2)

    @factory.lazy_attribute
    def registration_date_to(self):
        now = timezone.now().date()
        mode = self._state.registration
        if mode == PeriodState.before:
            return now + timedelta(days=20)
        elif mode == PeriodState.after:
            return now - timedelta(days=5)
        else:  # mode == PeriodState.during:
            return now + timedelta(days=2)

    @factory.lazy_attribute
    def delivery_date_from(self):
        now = timezone.now().date()
        mode = self._state.delivery
        if mode == PeriodState.before:
            return now + timedelta(days=10)
        elif mode == PeriodState.after:
            return now - timedelta(days=7)
        else:  # mode == PeriodState.during:
            return now - timedelta(days=1)

    @factory.lazy_attribute
    def delivery_date_to(self):
        now = timezone.now().date()
        mode = self._state.delivery
        if mode == PeriodState.before:
            return now + timedelta(days=20)
        elif mode == PeriodState.after:
            return now - timedelta(days=1)
        else:  # mode == PeriodState.during:
            return now + timedelta(days=5)

    @factory.lazy_attribute
    def judging_date_from(self):
        now = timezone.now().date()
        mode = self._state.judging
        if mode == PeriodState.before:
            return now + timedelta(days=20)
        elif mode == PeriodState.after:
            return now - timedelta(days=7)
        else:  # mode == PeriodState.during:
            return now - timedelta(days=1)

    @factory.lazy_attribute
    def judging_date_to(self):
        now = timezone.now().date()
        mode = self._state.judging
        if mode == PeriodState.before:
            return now + timedelta(days=25)
        elif mode == PeriodState.after:
            return now - timedelta(days=2)
        else:  # mode == PeriodState.during:
            return now + timedelta(days=5)

    # --- Publication flags and times ---
    competition_is_published = factory.LazyAttribute(
        lambda o: o._state.competition_is_published
    )
    result_is_published = factory.LazyAttribute(lambda o: o._state.result_is_published)
    competition_autopublish_datetime = factory.LazyAttribute(
        lambda o: o._state.competition_autopublish_datetime
    )
    result_autopublish_datetime = factory.LazyAttribute(
        lambda o: o._state.result_autopublish_datetime
    )
    # --- Judging flags ---
    is_judging_eliminations = factory.LazyAttribute(
        lambda o: o._state.is_judging_eliminations
    )
    is_judging_finals = factory.LazyAttribute(lambda o: o._state.is_judging_finals)
    is_judging_bos = factory.LazyAttribute(lambda o: o._state.is_judging_bos)
    bos_entry = None  # Optional, connect via subfactory as needed
    created_by = None
    modified_by = None

    def __new__(cls, *args: Any, **kwargs: Any) -> Contest:
        return super().__new__(cls)(*args, **kwargs)

    # @factory.post_generation
    # def styles(self, create, extracted, **kwargs):
    #     # Optionally attach styles here
    #     if extracted:
    #         for style in extracted:
    #             self.styles.add(style)
    #
    # @factory.post_generation
    # def payment_methods(self, create, extracted, **kwargs):
    #     if not create:
    #         # Simple build, do nothing
    #         return
    #     # If a list/iterable is supplied, use those objects
    #     if extracted:
    #         for method in extracted:
    #             self.payment_methods.add(method)
    #     else:
    #         # Otherwise, assign existing method with code="fake"
    #         try:
    #             method = PaymentMethod.objects.get(code="fake")
    #             self.payment_methods.add(method)
    #         except PaymentMethod.DoesNotExist:
    #             # Optionally raise or skip if not present
    #             pass
