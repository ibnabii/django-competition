from contest.factories import ContestFactory
from django.test import TestCase
from django.urls import reverse

from contest.tests.conftest import warn_on_repeated_table_queries


class FirstPageTests(TestCase):
    @warn_on_repeated_table_queries
    def check_redirected_to_home(self):
        response = self.client.get("", follow=True)
        self.assertRedirects(
            response,
            reverse("contest:contest_list"),
            status_code=302,
            target_status_code=200,
            fetch_redirect_response=True,
        )
        return response

    def check_no_contests(self):
        response = self.check_redirected_to_home()
        self.assertContains(response, "No contests available")
        return True

    def check_one_contest_redirected(self):
        response = self.client.get("", follow=True)
        self.assertRedirects(
            response,
            reverse("contest:contest_detail", kwargs={"slug": "published"}),
            status_code=302,
            target_status_code=200,
            fetch_redirect_response=True,
        )
        return True

    def test_zero_contests(self):
        self.assertEqual(self.check_no_contests(), True)

    def test_only_unpublished_contests(self):
        ContestFactory(title="Unpublished contest", competition_is_published=False)
        self.assertEqual(self.check_no_contests(), True)

    def test_one_published_contest(self):
        ContestFactory(title="Unpublished contest", competition_is_published=False)
        ContestFactory(
            title="Published contest", slug="published", competition_is_published=True
        )
        self.assertEqual(self.check_one_contest_redirected(), True)

    def test_multiple_published_contests(self):
        ContestFactory(title="Unpublished contest", competition_is_published=False)
        ContestFactory(title="PublishedContest1", competition_is_published=True)
        ContestFactory(title="PublishedContest2", competition_is_published=True)

        response = self.check_redirected_to_home()
        self.assertContains(response, "PublishedContest1")
        self.assertContains(response, "PublishedContest2")
