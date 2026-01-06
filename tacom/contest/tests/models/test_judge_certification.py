import pytest
from contest.factories import UserFactory
from contest.models.judges import JudgeCertification
from django.core.exceptions import ValidationError
from django.test import TestCase


@pytest.mark.unit
class JudgeCertificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory.create()

    def test_clean_valid_mead_bjcp_only(self):
        cert = JudgeCertification(user=self.user, is_mead_bjcp=True)
        cert.clean()  # Should not raise
        self.assertIsNone(cert.mjp_level)
        self.assertEqual(cert.other_description, "")

    def test_clean_valid_mjp_with_level(self):
        cert = JudgeCertification(user=self.user, is_mjp=True, mjp_level=3)
        cert.clean()  # Should not raise
        self.assertEqual(cert.mjp_level, 3)

    def test_clean_valid_other_with_description(self):
        cert = JudgeCertification(
            user=self.user, is_other=True, other_description="Some cert"
        )
        cert.clean()  # Should not raise
        self.assertEqual(cert.other_description, "Some cert")

    def test_clean_valid_multiple_certifications(self):
        cert = JudgeCertification(
            user=self.user,
            is_mead_bjcp=True,
            is_mjp=True,
            mjp_level=2,
            is_other=True,
            other_description="Desc",
        )
        cert.clean()  # Should not raise

    def test_clean_invalid_mjp_without_level(self):
        cert = JudgeCertification(user=self.user, is_mjp=True, mjp_level=None)
        with self.assertRaises(ValidationError) as cm:
            cert.clean()
        self.assertIn("mjp_level", cm.exception.message_dict)

    def test_clean_invalid_other_without_description(self):
        cert = JudgeCertification(user=self.user, is_other=True, other_description="")
        with self.assertRaises(ValidationError) as cm:
            cert.clean()
        self.assertIn("other_description", cm.exception.message_dict)

    def test_clean_invalid_other_blank_description(self):
        cert = JudgeCertification(
            user=self.user, is_other=True, other_description="   "
        )
        with self.assertRaises(ValidationError) as cm:
            cert.clean()
        self.assertIn("other_description", cm.exception.message_dict)

    def test_clean_clears_mjp_level_when_unchecked(self):
        cert = JudgeCertification(user=self.user, is_mjp=False, mjp_level=4)
        cert.clean()
        self.assertIsNone(cert.mjp_level)

    def test_clean_clears_other_description_when_unchecked(self):
        cert = JudgeCertification(
            user=self.user, is_other=False, other_description="Test"
        )
        cert.clean()
        self.assertEqual(cert.other_description, "")

    def test_save_valid_with_certifications(self):
        cert = JudgeCertification(user=self.user, is_mead_bjcp=True)
        cert.save()  # Should not raise
        self.assertTrue(JudgeCertification.objects.filter(user=self.user).exists())

    def test_save_invalid_without_any_certification(self):
        cert = JudgeCertification(user=self.user)  # All False
        with self.assertRaises(ValueError) as cm:
            cert.save()
        self.assertIn(
            "At least one certification type must be selected", str(cm.exception)
        )

    def test_one_to_one_constraint(self):
        JudgeCertification.objects.create(user=self.user, is_mead_bjcp=True)
        with self.assertRaises(Exception):  # IntegrityError or similar
            JudgeCertification.objects.create(user=self.user, is_other=True)
