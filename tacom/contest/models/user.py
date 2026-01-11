from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField


# from contest.managers import UserManager


def validate_gdpr_consent(value):
    if not value:
        raise ValidationError("You must accept Privacy Policy to create an account.")


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_("Email must be set"))

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("email address"), unique=True)

    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    country = CountryField(verbose_name=_("Country"), blank=True)
    phone = models.CharField(_("Phone number"), max_length=15, blank=True)
    address = models.CharField(_("Address"), max_length=200, blank=True)

    class JudgingLanguage(models.TextChoices):
        polish = "pl", _("Polish")
        english = "en", _("English")

    language = models.CharField(
        _("I would like to get feedback on my meads in"),
        choices=JudgingLanguage.choices,
        blank=True,
        max_length=2,
    )

    gdpr_consent = models.BooleanField(
        default=False,
        validators=[validate_gdpr_consent],
        verbose_name=_("Privacy Policy accepted"),
    )
    gdpr_consent_date = models.DateTimeField(auto_now_add=True)

    rebate_code_text = models.CharField(
        _("Rebate code"),
        max_length=15,
        blank=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "auth_user"

    def __str__(self):
        if self.last_name and self.first_name:
            return f"{self.last_name} {self.first_name}"
        return self.email

    @cached_property
    def profile_complete(self):
        return (
            self.first_name
            and self.last_name
            and self.country
            and self.phone
            and self.address
            and self.language
        )

    @cached_property
    def contest(self):
        # temp solution for one-competition site
        from contest.models import Contest

        return Contest.objects.first().slug


class Participant(User):
    class Meta:
        proxy = True
        verbose_name = _("Participant")
        verbose_name_plural = _("Participants")

    @property
    def entries_stats(self, contest=None):
        entries_qs = self.entries.all()
        if contest:
            entries_qs = entries_qs.filter(category__contest=contest)

        entries = (
            entries_qs.values("is_paid", "is_received")
            # .annotate(paid=models.Count('is_paid'), received=models.Count('is_received'))
            .annotate(count=models.Count("is_paid"))
        )
        return {
            "total": entries.aggregate(total=models.Sum("count")).get("total") or 0,
            "paid": entries.filter(is_paid=True).count(),
            "received": entries.filter(is_received=True).count(),
        }

    @property
    def entries_total(self):
        return self.entries_stats.get("total")

    entries_total.fget.short_description = _("Registered")

    @property
    def entries_paid(self):
        return self.entries_stats.get("paid")

    entries_paid.fget.short_description = _("Paid")

    @property
    def entries_received(self):
        return self.entries_stats.get("received")

    entries_received.fget.short_description = _("Received")
