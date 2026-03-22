from types import SimpleNamespace

import pytest
from django.test import TestCase

from contest.factories.contest_factory import ContestFactory
from contest.factories.user_factory import UserFactory
from contest.models.membership import ContestMembership
from contest.permissions.roles import Role


@pytest.mark.unit
@pytest.mark.roles
class RolesAssignmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = UserFactory.create(profile=True, judge=True)
        cls.user2 = UserFactory.create(profile=True, judge=True)
        cls.contest1 = ContestFactory()
        cls.contest2 = ContestFactory()

    def test_assign_judge_to_contest(self):
        role = Role.JUDGE

        # user didn't have contest membership yet
        has_membership = ContestMembership.objects.filter(
            user=self.user1, contest=self.contest1
        ).exists()
        self.assertFalse(has_membership)

        ContestMembership.set_role(self.user1, self.contest1, role, True)
        # now user has membership
        membership = ContestMembership.objects.filter(
            user=self.user1, contest=self.contest1
        )
        self.assertEqual(membership.count(), 1)
        self.assertEqual(membership[0].roles.first().role, role.value)
        self.assertEqual(membership[0].user, self.user1)
        self.assertEqual(membership[0].contest, self.contest1)
        # and does not have membership in the other contest
        has_membership = ContestMembership.objects.filter(
            user=self.user1, contest=self.contest2
        ).exists()
        self.assertFalse(has_membership)
        # and the other user does not have membership in this contest
        has_membership = ContestMembership.objects.filter(
            user=self.user2, contest=self.contest1
        ).exists()
        self.assertFalse(has_membership)

    def test_assign_2_roles_to_contest(self):
        roles = [Role.JUDGE_FINALS, Role.JUDGE_BOS]

        # user didn't have contest membership yet
        has_membership = ContestMembership.objects.filter(
            user=self.user1, contest=self.contest1
        ).exists()
        self.assertFalse(has_membership)

        for role in roles:
            ContestMembership.set_role(self.user1, self.contest1, role, True)
        # now user has membership
        membership = ContestMembership.objects.filter(
            user=self.user1, contest=self.contest1
        )
        self.assertEqual(membership.count(), 1)
        self.assertEqual(membership[0].roles.count(), 2)
        for role in roles:
            self.assertIn(
                role.value, membership[0].roles.all().values_list("role", flat=True)
            )

    def test_assign_role_to_2_contests(self):
        role = Role.JUDGE
        for contest in [self.contest1, self.contest2]:
            ContestMembership.set_role(self.user1, contest, role, True)
        memberships = ContestMembership.objects.filter(user=self.user1)
        self.assertEqual(memberships.count(), 2)
        for membership in memberships:
            self.assertEqual(membership.roles.first().role, role.value)

        # the other user
        memberships = ContestMembership.objects.filter(user=self.user2)
        self.assertEqual(memberships.count(), 0)

    def test_assign_role_twice(self):
        role = Role.JUDGE
        ContestMembership.set_role(self.user1, self.contest1, role, True)
        ContestMembership.set_role(self.user1, self.contest1, role, True)
        memberships = ContestMembership.objects.filter(user=self.user1)
        self.assertEqual(memberships.count(), 1)
        self.assertEqual(memberships[0].roles.first().role, role.value)

    def test_assign_non_existent_role(self):
        with self.assertRaises(ValueError):
            ContestMembership.set_role(
                self.user1,
                self.contest1,
                SimpleNamespace(value="Not existent role"),  # type: ignore
                True,
            )


@pytest.mark.unit
@pytest.mark.roles
class RolesRemovalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = UserFactory.create(profile=True, judge=True)
        cls.user2 = UserFactory.create(profile=True, judge=True)
        cls.contest1 = ContestFactory()
        cls.contest2 = ContestFactory()
        cls.roles = [Role.JUDGE, Role.JUDGE_FINALS]
        for role in cls.roles:
            for contest in [cls.contest1, cls.contest2]:
                for user in [cls.user1, cls.user2]:
                    ContestMembership.set_role(user, contest, role, True)

    def test_remove_all_roles(self):
        for role in self.roles:
            ContestMembership.set_role(self.user1, self.contest1, role, False)

        # removed membership from contest1
        memberships = ContestMembership.objects.filter(
            user=self.user1, contest=self.contest1
        ).exists()
        self.assertFalse(memberships)

        # not touched contest2
        memberships = ContestMembership.objects.filter(
            user=self.user1, contest=self.contest2
        )
        self.assertEqual(memberships.count(), 1)
        self.assertEqual(memberships.first().roles.count(), 2)

        # not touched other users
        memberships = ContestMembership.objects.filter(user=self.user2)
        self.assertEqual(memberships.count(), 2)
        for membership in memberships:
            self.assertEqual(membership.roles.count(), 2)

    def test_remove_one_of_multiple_roles(self):
        ContestMembership.set_role(self.user1, self.contest1, self.roles[0], False)
        # still has other role in contest 1
        membership = ContestMembership.objects.get(
            user=self.user1, contest=self.contest1
        )
        self.assertEqual(membership.roles.count(), 1)
        self.assertEqual(membership.roles.first().role, self.roles[1].value)

        # still has two memberships
        memberships = ContestMembership.objects.filter(user=self.user1)
        self.assertEqual(memberships.count(), 2)

    def test_remove_role_not_assigned(self):
        ContestMembership.set_role(self.user1, self.contest1, Role.JUDGE_BOS, False)
        # still has two memberships
        memberships = ContestMembership.objects.filter(user=self.user1)
        self.assertEqual(memberships.count(), 2)
        # still has two roles in contest1
        membership = ContestMembership.objects.get(
            user=self.user1, contest=self.contest1
        )
        self.assertEqual(membership.roles.count(), 2)
        for role in self.roles:
            self.assertIn(role.value, membership.roles.values_list("role", flat=True))

    def test_remove_role_from_user_witout_roles(self):
        user = UserFactory(profile=True, judge=True)
        ContestMembership.set_role(user, self.contest1, Role.JUDGE_BOS, False)

    def test_remove_role_from_cotnest_without_roles(self):
        contest = ContestFactory.create()
        ContestMembership.set_role(self.user1, contest, Role.JUDGE_BOS, False)

    def test_remove_role_for_invalid_user(self):
        ContestMembership.set_role(None, self.contest1, Role.JUDGE_BOS, False)

    def test_remove_role_for_invalid_contest(self):
        ContestMembership.set_role(self.user1, None, Role.JUDGE_BOS, False)

    def test_remove_role_for_invalid_role(self):
        ContestMembership.set_role(
            self.user1,
            self.contest1,
            SimpleNamespace(value="Not existent role"),  # type: ignore
            False,
        )
