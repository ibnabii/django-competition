import pytest
from contest.factories import (
    ContestFactory,
    ContestState,
    PeriodState,
    UserFactory,
)
from contest.models.judges import JudgeCertification, JudgeInCompetition
from django.test import TestCase
from django.urls import reverse


@pytest.mark.judges
class JudgeCertificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory.create()

    def setUp(self):
        self.client.force_login(self.user)

    def test_certification_detail_view_with_existing_certification(self):
        JudgeCertification.objects.create(user=self.user, is_mead_bjcp=True)
        url = reverse("contest:judge_certification_read")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "contest/judges/judge_certification_read.html"
        )
        self.assertIn("object", response.context)

    def test_certification_detail_view_without_certification(self):
        url = reverse("contest:judge_certification_read")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "contest/judges/judge_certification_empty.html"
        )

    def test_certification_update_view_get_object_existing(self):
        cert = JudgeCertification.objects.create(user=self.user, is_mead_bjcp=True)
        url = reverse("contest:judge_certification_edit")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["object"], cert)

    def test_certification_update_view_get_object_none(self):
        url = reverse("contest:judge_certification_edit")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context.get("object"))

    def test_certification_update_view_form_valid_with_certifications(self):
        url = reverse("contest:judge_certification_edit")
        data = {"is_mead_bjcp": True}
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse("contest:judge_certification_read"))
        self.assertTrue(JudgeCertification.objects.filter(user=self.user).exists())

    def test_certification_update_view_form_valid_without_certifications_deletes(self):
        JudgeCertification.objects.create(user=self.user, is_mead_bjcp=True)
        url = reverse("contest:judge_certification_edit")
        data = {"is_mead_bjcp": False, "is_mjp": False, "is_other": False}
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse("contest:judge_certification_read"))
        self.assertFalse(JudgeCertification.objects.filter(user=self.user).exists())


@pytest.mark.judges
@pytest.mark.widgets
class JudgeApplicationWidgetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.contest = ContestFactory(
            _state=ContestState(judge_registration=PeriodState.during)
        )
        cls.user = UserFactory.create(profile=True)
        cls.url = reverse(
            "contest:judge_application_widget", kwargs={"slug": cls.contest.slug}
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_widget_view_no_application(self):

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "contest/judges/widgets/apply.html")

    def test_widget_view_application_pending(self):
        JudgeInCompetition.objects.create(user=self.user, contest=self.contest)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "contest/judges/widgets/applied.html")

    def test_widget_view_application_approved(self):
        JudgeInCompetition.objects.create(
            user=self.user,
            contest=self.contest,
            status=JudgeInCompetition.Status.APPROVED,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "contest/judges/widgets/applied.html")

    def test_widget_view_application_rejected(self):
        JudgeInCompetition.objects.create(
            user=self.user,
            contest=self.contest,
            status=JudgeInCompetition.Status.REJECTED,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "contest/judges/widgets/rejected.html")


@pytest.mark.judges
@pytest.mark.unit
class JudgeApplicationPolicyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.contest = ContestFactory(
            _state=ContestState(judge_registration=PeriodState.during)
        )
        cls.user = UserFactory.create(profile=True)

    def setUp(self):
        self.client.force_login(self.user)
        # Mock a view with the mixins
        from contest.views.judges import JudgeApplicationCreateView

        self.view = JudgeApplicationCreateView()
        self.view.request = self.client.request().wsgi_request
        self.view.contest = self.contest

    def test_can_apply_no_certification(self):
        result = self.view.can_apply()
        self.assertFalse(result.allowed)
        self.assertIn("certificates", str(result.reason))

    def test_can_apply_with_certification_no_application(self):
        JudgeCertification.objects.create(user=self.user, is_mead_bjcp=True)
        result = self.view.can_apply()
        self.assertTrue(result.allowed)

    def test_can_apply_already_applied(self):
        JudgeCertification.objects.create(user=self.user, is_mead_bjcp=True)
        JudgeInCompetition.objects.create(user=self.user, contest=self.contest)
        self.view.application = JudgeInCompetition.objects.get(
            user=self.user, contest=self.contest
        )
        result = self.view.can_apply()
        self.assertFalse(result.allowed)
        self.assertIn("already applied", str(result.reason))

    def test_can_withdraw_no_application(self):
        result = self.view.can_withdraw()
        self.assertFalse(result.allowed)
        self.assertIn("not applied", str(result.reason))

    def test_can_withdraw_rejected(self):
        JudgeInCompetition.objects.create(
            user=self.user,
            contest=self.contest,
            status=JudgeInCompetition.Status.REJECTED,
        )
        self.view.application = JudgeInCompetition.objects.get(
            user=self.user, contest=self.contest
        )
        result = self.view.can_withdraw()
        self.assertFalse(result.allowed)
        self.assertIn("rejected", str(result.reason))

    def test_can_withdraw_allowed(self):
        JudgeInCompetition.objects.create(user=self.user, contest=self.contest)
        self.view.application = JudgeInCompetition.objects.get(
            user=self.user, contest=self.contest
        )
        result = self.view.can_withdraw()
        self.assertTrue(result.allowed)
