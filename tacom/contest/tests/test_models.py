from datetime import datetime
from time import sleep

from django.test import TestCase

from contest.models import Contest


class ContestModelTests(TestCase):
    def test_slugify_unique(self):
        c1 = Contest.objects.create(
            title="Test test test"
        )
        c2 = Contest.objects.create(
            title="Test test test"
        )
        self.assertNotEqual(c1.slug, c2.slug)

    def test_slug_no_change(self):
        c1 = Contest.objects.create(
            title="Test test test"
        )
        s1 = c1.slug
        c1.title = 'Hokus pokus'
        c1.save()
        self.assertEqual(s1, c1.slug)

    def test_timestamps(self):
        c1 = Contest.objects.create(
            title="Test test test"
        )
        c2 = Contest.objects.create(
            title="Test test test"
        )
        self.assertEqual(c1.created_at.strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self.assertEqual(c1.created_at.strftime('%Y-%m-%d %H:%M:%S'), c2.created_at.strftime('%Y-%m-%d %H:%M:%S'))
        self.assertEqual(c1.created_at, c1.modified_at)

        sleep(1)
        c1.title = 'abcd'
        c1.save()
        self.assertNotEqual(c1.created_at, c1.modified_at)
        self.assertEqual(c1.modified_at.strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self.assertEqual(c1.created_at.strftime('%Y-%m-%d %H:%M:%S'), c2.created_at.strftime('%Y-%m-%d %H:%M:%S'))

