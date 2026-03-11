import random
from typing import TYPE_CHECKING, Any

import factory
from faker import Faker

from contest.models import User
from contest.models.judges import JudgeCertification, JudgeInCompetition
from factories import RandomLocaleDjangoModelFactory


class UserFactory(RandomLocaleDjangoModelFactory):
    class Meta:
        model = User
        exclude = ("profile", "judge")

    email = factory.LazyAttribute(lambda o: o.faker.email())
    gdpr_consent = True

    # for typing only
    if TYPE_CHECKING:

        def __call__(self, *args: Any, **kwargs: Any) -> User: ...

        @classmethod
        def create(cls, **kwargs: Any) -> User: ...

        @classmethod
        def build(cls, **kwargs: Any) -> User: ...

    # now the "specific" Users

    # User by default has no profile or judge certification
    profile = False
    judge = False

    class Params:
        profile = factory.Trait(
            first_name=factory.LazyAttribute(lambda o: o.faker.first_name()),
            last_name=factory.LazyAttribute(lambda o: o.faker.last_name()),
            country=factory.LazyAttribute(lambda o: o.faker.country_code()),
            phone=factory.LazyAttribute(lambda o: o.faker.phone_number()),
            address=factory.LazyAttribute(lambda o: o.faker.address()),
            language=factory.LazyAttribute(
                lambda o: "pl" if getattr(o, "_locale", "") == "pl_PL" else "en"
            ),
        )
        judge = factory.Trait(
            judge_certification=factory.RelatedFactory(
                "contest.factories.user_factory.JudgeCertificationFactory",
                factory_related_name="user",
            )
        )


_CERT_CYCLE = ["bjcp", "mjp", "other"]


class JudgeCertificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = JudgeCertification
        exclude = ("_cert_type",)

    user = None  # provided via RelatedFactory

    # cycle BJCP → MJP → Other deterministically
    _cert_type = factory.Sequence(lambda n: _CERT_CYCLE[n % len(_CERT_CYCLE)])

    is_mead_bjcp = factory.LazyAttribute(lambda o: o._cert_type == "bjcp")
    is_mjp = factory.LazyAttribute(lambda o: o._cert_type == "mjp")
    is_other = factory.LazyAttribute(lambda o: o._cert_type == "other")

    tshirt_size = factory.LazyAttribute(
        lambda o: random.choice([s[0] for s in JudgeCertification.TShirtSize.choices])
    )

    mjp_level = factory.LazyAttribute(
        lambda o: random.randint(1, 5) if o.is_mjp else None
    )
    other_description = factory.LazyAttribute(
        lambda o: (Faker().sentence(nb_words=15) if o.is_other else "")
    )


class JudgeApplicationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = JudgeInCompetition

    contest = None
    user = factory.LazyAttribute(lambda o: UserFactory.create(profile=True, judge=True))

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        if kwargs.get("contest") is None:
            raise ValueError("JudgeApplicationFactory requires a 'contest' argument.")
        return super()._create(model_class, *args, **kwargs)
