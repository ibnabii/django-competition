import pytest
from django.test import TestCase

from contest.factories.category_factory import CategoryFactory
from contest.factories.contest_factory import ContestFactory
from contest.factories.entry_factory import EntryFactory
from contest.factories.style_factory import StyleFactory
from contest.factories.user_factory import UserFactory


@pytest.mark.unit
@pytest.mark.entries
class EntryCodeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        style = StyleFactory()
        cls.contest1 = ContestFactory(
            categories=[CategoryFactory(style=style), CategoryFactory()]
        )
        cls.contest2 = ContestFactory(
            categories=[CategoryFactory(style=style), CategoryFactory()]
        )
        cls.brewer = UserFactory(profile=True)

    def test_first_entry_in_competition_is_1000(self):
        entry = EntryFactory(
            category=self.contest1.categories.first(), brewer=self.brewer
        )
        self.assertEqual(entry.code, 1000)

    def test_first_entry_in_every_competition_is_1000_same_categories(self):
        entry1 = EntryFactory(
            category=self.contest1.categories.first(), brewer=self.brewer
        )
        entry2 = EntryFactory(
            category=self.contest2.categories.first(), brewer=self.brewer
        )
        self.assertEqual(entry1.code, 1000)
        self.assertEqual(entry2.code, 1000)

    def test_first_entry_in_every_competition_is_1000_different_categories(self):
        entry1 = EntryFactory(
            category=self.contest1.categories.last(), brewer=self.brewer
        )
        entry2 = EntryFactory(
            category=self.contest2.categories.last(), brewer=self.brewer
        )
        self.assertEqual(entry1.code, 1000)
        self.assertEqual(entry2.code, 1000)

    def test_entries_get_next_values_codes(self):
        categories = [category for category in self.contest1.categories.all()]
        for i in range(20):
            with self.subTest(idx=i, category=categories[i % 2].style.name):
                kwargs = {}
                if i % 3:
                    kwargs["brewer"] = self.brewer
                entry = EntryFactory(category=categories[i % 2], **kwargs)
                self.assertEqual(entry.code, 1000 + i)
