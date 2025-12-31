from datetime import datetime
from time import sleep

from contest.factories import ContestFactory
from django.test import TestCase


class ContestModelTests(TestCase):
    def test_slugify_unique(self):
        c1 = ContestFactory(title="Test test test")
        c2 = ContestFactory(title="Test test test")
        self.assertNotEqual(c1.slug, c2.slug)

    def test_slug_no_change(self):
        c1 = ContestFactory(title="Test test test")
        s1 = c1.slug
        c1.title = "Hokus pokus"
        c1.save()
        self.assertEqual(s1, c1.slug)

    def test_timestamps(self):
        c1 = ContestFactory(title="Test test test")
        c2 = ContestFactory(title="Test test test")
        now = datetime.now()
        self.assertLessEqual(abs((c1.created_at - now).total_seconds()), 1)

        self.assertLessEqual(abs((c1.created_at - c2.created_at).total_seconds()), 1)

        self.assertEqual(c1.created_at, c1.modified_at)

        sleep(1)
        c1.title = "abcd"
        c1.save()
        now = datetime.now()

        self.assertNotEqual(c1.created_at, c1.modified_at)

        self.assertLessEqual(abs((c1.modified_at - now).total_seconds()), 1)

        self.assertLessEqual(abs((c1.created_at - c2.created_at).total_seconds()), 1)
