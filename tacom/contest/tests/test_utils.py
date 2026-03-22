# Test utitilites functions
import pytest
from django.test import TestCase

from contest.factories.contest_factory import ContestFactory
from contest.factories.user_factory import UserFactory
from contest.models import Contest
from contest.models.membership import ContestMembership
from contest.permissions.roles import Role
from contest.utils import get_role_state


@pytest.mark.unit
@pytest.mark.roles
class TestGetRoleState(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = UserFactory(profile=True, judge=True)
        cls.user2 = UserFactory(profile=True, judge=True)
        cls.contest1 = ContestFactory.create()
        cls.contest2 = ContestFactory.create()
        cls.roles = [Role.JUDGE, Role.JUDGE_FINALS]
        cls.unassigned_role = Role.JUDGE_BOS
        for role in cls.roles:
            ContestMembership.set_role(cls.user1, cls.contest1, role, True)

    def test_user_has_role(self):
        for role in self.roles:
            self.assertTrue(get_role_state(self.user1, self.contest1, role))

    def test_user_doesnt_have_unassigned_role(self):
        self.assertFalse(
            get_role_state(self.user1, self.contest1, self.unassigned_role)
        )

    def test_user_doesnt_have_role_in_other_contest(self):
        for role in [*self.roles, self.unassigned_role]:
            self.assertFalse(get_role_state(self.user1, self.contest2, role))

    def test_other_user_doesnt_have_role(self):
        for role in self.roles:
            self.assertFalse(get_role_state(self.user2, self.contest1, role))
