import pytest
from contest.factories import ContestFactory, UserFactory
from contest.models.judges import JudgeInCompetition
from django.db import IntegrityError
from django.test import TestCase


@pytest.mark.unit
@pytest.mark.judges
class JudgeInCompetitionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory.create()
        cls.contest = ContestFactory.create()

    def test_default_status_is_application(self):
        judge = JudgeInCompetition.objects.create(user=self.user, contest=self.contest)
        self.assertEqual(judge.status, JudgeInCompetition.Status.APPLICATION)

    def test_unique_constraint_prevents_duplicate_user_contest(self):
        JudgeInCompetition.objects.create(user=self.user, contest=self.contest)
        with self.assertRaises(IntegrityError):
            JudgeInCompetition.objects.create(user=self.user, contest=self.contest)

    def test_status_choices_are_valid(self):
        for status in JudgeInCompetition.Status.choices:
            judge = JudgeInCompetition.objects.create(
                user=self.user, contest=self.contest, status=status[0]
            )
            self.assertEqual(judge.status, status[0])
            judge.delete()

    def test_approved_judge_manager_filters_correctly(self):
        # Create judges with different statuses
        app_judge = JudgeInCompetition.objects.create(
            user=self.user,
            contest=self.contest,
            status=JudgeInCompetition.Status.APPLICATION,
        )
        approved_judge = JudgeInCompetition.objects.create(
            user=UserFactory.create(),
            contest=self.contest,
            status=JudgeInCompetition.Status.APPROVED,
        )
        rejected_judge = JudgeInCompetition.objects.create(
            user=UserFactory.create(),
            contest=self.contest,
            status=JudgeInCompetition.Status.REJECTED,
        )

        approved_queryset = JudgeInCompetition.approved.get_queryset()
        self.assertIn(approved_judge, approved_queryset)
        self.assertNotIn(app_judge, approved_queryset)
        self.assertNotIn(rejected_judge, approved_queryset)

    def test_meta_verbose_names(self):
        JudgeInCompetition.objects.create(user=self.user, contest=self.contest)
        self.assertEqual(str(JudgeInCompetition._meta.verbose_name), "Judge")
        self.assertEqual(str(JudgeInCompetition._meta.verbose_name_plural), "Judges")
