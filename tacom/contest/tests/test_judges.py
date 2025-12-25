import pytest
from django.templatetags.i18n import language
from django.utils.translation import override

from contest.factories import ContestFactory, ContestState, PeriodState
from contest.models import User
from django.test import TestCase
from django.urls import reverse

from contest.models.judges import JudgeInCompetition, JudgeCertification


@pytest.mark.judges
class JudgeRegistrationJourneyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.contest = ContestFactory(
            _state=ContestState(judge_registration=PeriodState.during)
        )
        cls.contest_no_registration = ContestFactory(
            _state=ContestState(judge_registration=PeriodState.after)
        )
        cls.user = User.objects.create_user(
            username="testuser",
            first_name="Test",
            last_name="User",
            country="CZ",
            phone="123",
            address="abc",
            language="en",
        )

        # TODO: add profile for testuser
        cls.user_no_profile = User.objects.create_user(username="testuser2")

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

    def test_logged_in_user_needs_full_profile(self):
        self.client.force_login(self.user_no_profile)
        url = reverse(
            "contest:judge_application",
            kwargs={"slug": self.contest.slug},
        )
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        profile_url = reverse("contest:profile_edit")
        self.assertRedirects(response, profile_url)

    def test_logged_in_user_can_apply(self):
        self.client.force_login(self.user)
        url = reverse(
            "contest:judge_application",
            kwargs={"slug": self.contest.slug},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


@pytest.mark.judges
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


@pytest.mark.judges
@pytest.mark.unit
class JudgeApplicationActionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.contest = ContestFactory(
            _state=ContestState(judge_registration=PeriodState.during)
        )
        # User with full profile
        cls.user = User.objects.create_user(
            first_name="John",
            last_name="Doe",
            country="PL",
            phone="123",
            address="Street",
            language="en",
            username="testuser",
        )
        cls.apply_url = reverse(
            "contest:judge_widget_apply", kwargs={"slug": cls.contest.slug}
        )
        cls.cancel_url = reverse(
            "contest:judge_widget_cancel", kwargs={"slug": cls.contest.slug}
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_apply_fails_without_certification(self):
        response = self.client.post(self.apply_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("X-Application-Error"), "True")
        self.assertFalse(JudgeInCompetition.objects.filter(user=self.user).exists())

    def test_apply_success_with_certification(self):
        JudgeCertification.objects.create(user=self.user, is_mead_bjcp=True)

        response = self.client.post(self.apply_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("X-Application-Error", response.headers)
        self.assertTrue(JudgeInCompetition.objects.filter(user=self.user).exists())

    def test_apply_fails_if_already_applied(self):
        JudgeCertification.objects.create(user=self.user, is_mead_bjcp=True)
        JudgeInCompetition.objects.create(user=self.user, contest=self.contest)

        response = self.client.post(self.apply_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("X-Application-Error"), "True")
        # Still only one
        self.assertEqual(JudgeInCompetition.objects.filter(user=self.user).count(), 1)

    def test_cancel_success(self):
        JudgeInCompetition.objects.create(user=self.user, contest=self.contest)

        response = self.client.post(self.cancel_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("X-Application-Error", response.headers)
        self.assertFalse(JudgeInCompetition.objects.filter(user=self.user).exists())

    def test_cancel_fails_if_not_applied(self):
        response = self.client.post(self.cancel_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("X-Application-Error"), "True")

    def test_cancel_fails_if_rejected(self):
        application = JudgeInCompetition.objects.create(
            user=self.user,
            contest=self.contest,
            status=JudgeInCompetition.Status.REJECTED,
        )

        response = self.client.post(self.cancel_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("X-Application-Error"), "True")
        # Application still exists
        self.assertTrue(JudgeInCompetition.objects.filter(id=application.id).exists())
