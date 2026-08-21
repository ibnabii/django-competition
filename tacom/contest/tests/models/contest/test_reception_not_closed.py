import pytest
from dataclasses import dataclass
from datetime import date, timedelta

from contest.factories.contest_factory import ContestFactory
from contest.models import Contest


@dataclass
class Case:
    name: str
    factory_kwargs: dict
    expected: bool

today = date.today()
past = today - timedelta(days=1)
future = today + timedelta(days=1)

CASES = [
    Case("Null from and to", {"delivery_date_from": None, "delivery_date_to": None}, True),

    Case("From in past, null to", {"delivery_date_from": past, "delivery_date_to": None}, True),
    Case("From in future, null to", {"delivery_date_from": future, "delivery_date_to": None}, True),

    Case("Null from, delivery closed", {"delivery_date_from": None, "delivery_date_to": past}, False),
    Case("Null from, delivery till today", {"delivery_date_from": None, "delivery_date_to": today}, True),
    Case("Null from, delivery till future", {"delivery_date_from": None, "delivery_date_to": future}, True),

    Case("From in past, delivery closed", {"delivery_date_from": past, "delivery_date_to": past}, False),
    Case("From in past, delivery till today", {"delivery_date_from": past, "delivery_date_to": today}, True),
    Case("From in past, delivery till future", {"delivery_date_from": past, "delivery_date_to": future}, True),

    Case("From in future, delivery closed", {"delivery_date_from": future, "delivery_date_to": past}, False),
    Case("From in future, delivery till today", {"delivery_date_from": future, "delivery_date_to": today}, True),
    Case("From in future, delivery till future", {"delivery_date_from": future, "delivery_date_to": future}, True),

]

@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
@pytest.mark.django_db
def test_reception_not_closed(case):
    contest = ContestFactory.create(
        title=case.name,
        **case.factory_kwargs,
    )

    assert contest.is_reception_not_closed is case.expected
    assert Contest.reception_not_closed.filter(pk=contest.pk).exists() is case.expected