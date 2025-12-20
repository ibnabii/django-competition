from django.test import TestCase
from django.urls import reverse

from contest.factories import ContestFactory, ContestState, PeriodState
from contest.models import User


class JudgeRegistrationJourneyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.contest = ContestFactory(
            _state=ContestState(judge_registration=PeriodState.during)
        )
        cls.contest_no_registration = ContestFactory(
            _state=ContestState(judge_registration=PeriodState.after)
        )
        cls.user = User.objects.create_user(username="testuser")

    # TODO
    def get_url(self, slug): ...

    def test_no_registration_404(self):
        url = reverse(
            "contest:judge_application",
            kwargs={"slug": self.contest_no_registration.slug},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_application_redirect_to_login(self):
        url = reverse(
            "contest:judge_application",
            kwargs={"slug": self.contest.slug},
        )

        response = self.client.get(url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/login.html")

    def test_logged_in_user_can_apply(self):
        self.client.force_login(self.user)
        url = reverse(
            "contest:judge_application",
            kwargs={"slug": self.contest.slug},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class JudgeCertificationForLoggedInOnlyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.contest = ContestFactory(
            _state=ContestState(judge_registration=PeriodState.during)
        )
        cls.user = User.objects.create_user(username="testuser")
        cls.views = [
            "contest:judge_certification_read",
            "contest:judge_certification_edit",
        ]
        cls.urls = [reverse(view) for view in cls.views]

    def test_judge_certification_redirect_to_login(self):
        for idx, url in enumerate(self.urls):
            with self.subTest(url=self.views[idx]):
                response = self.client.get(url, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "account/login.html")

    def test_judge_certification_user_access(self):
        self.client.force_login(self.user)
        for idx, url in enumerate(self.urls):
            with self.subTest(url=self.views[idx]):
                response = self.client.get(url)
                self.assertIn(response.status_code, [200, 404])
