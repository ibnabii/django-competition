from contest.models import Contest, User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class JudgeCertification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_mead_bjcp = models.BooleanField(default=False, verbose_name=_("BJCP Mead"))
    is_mjp = models.BooleanField(default=False, verbose_name=_("MJP"))
    is_other = models.BooleanField(default=False, verbose_name=_("Other"))
    mjp_level = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_("MJP level"),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    other_description = models.TextField(blank=True, verbose_name=_("Description"))

    def clean(self):
        super().clean()

        # At least one certification must be selected
        # This was moved to save() as no certification (via dedicated view)
        # implies deletion of certification

        # if not (self.is_mead_bjcp or self.is_mjp or self.is_other):
        #     raise ValidationError(
        #         _("At least one certification type must be selected.")
        #     )

        # If MJP is selected, mjp_level must be provided
        if self.is_mjp and self.mjp_level is None:
            raise ValidationError(
                {
                    "mjp_level": _(
                        "MJP level is required when MJP certification is selected."
                    )
                }
            )

        # If Other is selected, other_description cannot be blank
        if self.is_other and not self.other_description.strip():
            raise ValidationError(
                {
                    "other_description": _(
                        "Description is required when Other certification is selected."
                    )
                }
            )
        # Clean extra fields if checkbox is unchecked
        if not self.is_mjp:
            self.mjp_level = None
        if not self.is_other:
            self.other_description = ""

    def save(self, *args, **kwargs):
        if not (self.is_mead_bjcp or self.is_mjp or self.is_other):
            raise ValueError("At least one certification type must be selected.")
        super().save(*args, **kwargs)


class JudgeInCompetition(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)

    class Status(models.TextChoices):
        APPLICATION = "application", "Application"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.APPLICATION
    )

    approved = "ApprovedJudgeManager"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "contest"],
                name="unique_judge_application_per_contest",
            )
        ]
        verbose_name = _("Judge")
        verbose_name_plural = _("Judges")


class ApprovedJudgeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=JudgeInCompetition.Status.APPROVED)
