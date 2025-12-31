import factory
from factories import RandomLocaleDjangoModelFactory
from contest.models import User


class UserFactory(RandomLocaleDjangoModelFactory):
    class Meta:
        model = User
        exclude = ("faker",)
