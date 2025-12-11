import pytest
from contest.admin import duplicate_contest
from contest.factories import ContestFactory
from contest.models import Contest
from django.test import TestCase
from django.utils.translation import override


@pytest.mark.admin
class DuplicateContestActionTest(TestCase):
    def setUp(self):
        ContestFactory()
        self.contest = ContestFactory()
        for _ in range(5):
            ContestFactory()
        ContestFactory(title="test1")
        ContestFactory(title="test2")

    def test_duplicate_contest_action_creates_copies_single(self):
        original_count = Contest.objects.count()

        # Run the admin action: pass None for modeladmin and request
        with override("en"):  # Ensures translation for 'copy'
            duplicate_contest(None, None, Contest.objects.filter(pk=self.contest.pk))

        self.assertEqual(Contest.objects.count(), original_count + 1)
        copied = Contest.objects.order_by("-id").first()
        self.assertEqual(copied.title, self.contest.title + " (copy)")
        self.assertNotEqual(copied.pk, self.contest.pk)
        self.assertNotEqual(
            copied.slug, self.contest.slug
        )  # Assuming slug auto-generated and unique
        self.assertTrue(copied.slug)  # Shouldn't be blank after save

    def test_duplicate_contest_action_creates_copies_multiple(self):
        original_count = Contest.objects.count()

        # Run the admin action: pass None for modeladmin and request
        with override("en"):  # Ensures translation for 'copy'
            duplicate_contest(
                None, None, Contest.objects.filter(title__in=["test1", "test2"])
            )

        self.assertEqual(Contest.objects.count(), original_count + 2)

        self.assertEqual(True, Contest.objects.filter(title="test1 (copy)").exists())
        self.assertEqual(True, Contest.objects.filter(title="test1").exists())
        self.assertEqual(True, Contest.objects.filter(title="test2").exists())
