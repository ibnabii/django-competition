import pytest
from django.core.exceptions import ValidationError
from django.test import TestCase

from contest.factories.category_factory import CategoryFactory
from contest.factories.contest_factory import ContestFactory
from contest.factories.entry_factory import EntryFactory
from contest.factories.style_factory import StyleFactory
from contest.factories.user_factory import UserFactory
from contest.models import Entry


@pytest.mark.unit
@pytest.mark.entries
class EntrySecretCodeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        style = StyleFactory()
        cls.categories = [CategoryFactory(style=style), CategoryFactory()]
        cls.contest = ContestFactory(
            categories=cls.categories,
        )
        cls.contest2 = ContestFactory(
            categories=[CategoryFactory() for _ in range(3)],
        )

    def test_secret_code_generated_and_unique(self):
        entries = [EntryFactory(contest=self.contest) for _ in range(100)]
        self.assertEqual(Entry.objects.filter(secret_code__isnull=True).exists(), False)
        self.assertEqual(
            len(entries), len(set([entry.secret_code for entry in entries]))
        )

    def test_secret_code_can_be_same_in_different_contests(self):
        entry1 = EntryFactory(contest=self.contest)
        entry2 = EntryFactory(contest=self.contest2, secret_code=entry1.secret_code)
        self.assertEqual(entry1.secret_code, entry2.secret_code)

    def test_secret_code_cannot_be_same_in_same_contests(self):
        entry1 = EntryFactory(contest=self.contest)
        with self.assertRaises(ValidationError):
            EntryFactory(contest=self.contest, secret_code=entry1.secret_code)
