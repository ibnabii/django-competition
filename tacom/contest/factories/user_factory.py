import factory
from contest.models import User
from factories import RandomLocaleDjangoModelFactory


class UserFactory(RandomLocaleDjangoModelFactory):
    class Meta:
        model = User
        exclude = ("profile", "judge")

    username = factory.LazyAttribute(lambda o: o.faker.user_name())
    email = factory.LazyAttribute(lambda o: o.faker.email())
    gdpr_consent = True

    # for typing only
    @classmethod
    def create(cls, **kwargs) -> User:
        return super().create(**kwargs)

    # now the "specific" Users

    # User by default has no profile or judge certification
    profile = False
    judge = False

    # @factory.post_generation
    # def profile_fields(self, create, extracted, **kwargs):
    #     if getattr(self, "profile", False):
    #         self.first_name = factory.LazyAttribute(lambda o: o.faker.first_name())
    #         self.last_name = factory.LazyAttribute(lambda o: o.faker.last_name())
    #         self.country = factory.LazyAttribute(lambda o: o.faker.country())
    #         self.phone = factory.LazyAttribute(lambda o: o.faker.phone_number())
    #         self.address = factory.LazyAttribute(lambda o: o.faker.address())
    #         self.language = "pl" if self._locale == "pl_PL" else "en"

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

        # @factory.trait  # type: ignore
        # def judge(self):
        #     factory.RelatedFactory("JudgeProfileFactory", factory_related_name="user")


#
# class JudgeProfileFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = JudgeProfile
#
#     user = factory.SubFactory(UserFactory, profile=False, judge=False)
#
#     expertise = factory.Faker("job")
#     years_experience = factory.Faker("random_int", min=1, max=20)
#     website = factory.Faker("url")
#     # ... other judge-specific fields
