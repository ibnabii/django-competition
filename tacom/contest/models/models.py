from datetime import date, datetime
from logging import getLogger
from random import choices
from string import ascii_uppercase, digits
from uuid import uuid1
from contest.managers import (
    CategoryManager,
    ContestManager,
    DefaultManager,
    PaymentManagerExcludeStatuses,
    PaymentMethodManager,
    PublishedContestManager,
    RegistrableContestManager,
    StyleManager,
)
from contest.utils import mail_entry_status_change
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.utils import OperationalError
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from simple_history.models import HistoricalRecords
from .user import User
from contest.utils import code_generator, rebate_code_generator

logger = getLogger("models")

# User = get_user_model()


def validate_gdpr_consent(value):
    if not value:
        raise ValidationError("You must accept Privacy Policy to create an account.")


# TODO: remove
#
# class User(AbstractUser):
#     class Meta:
#         db_table = "auth_user"
#
#     class JudgingLanguage(models.TextChoices):
#         polish = "pl", _("Polish")
#         english = "en", _("English")
#
#     country = CountryField(verbose_name=_("Country"), blank=True)
#     phone = models.CharField(max_length=15, verbose_name=_("Phone number"), blank=True)
#     address = models.CharField(max_length=200, blank=True, verbose_name=_("Address"))
#     language = models.CharField(
#         verbose_name=_("I would like to get feedback on my meads in"),
#         choices=JudgingLanguage.choices,
#         blank=True,
#         max_length=2,
#     )
#     gdpr_consent = models.BooleanField(
#         default=False,
#         validators=[validate_gdpr_consent],
#         verbose_name=_("Privacy Policy accepted"),
#     )
#     gdpr_consent_date = models.DateTimeField(auto_now_add=True)
#     rebate_code_text = models.CharField(
#         max_length=15,
#         verbose_name=_("Rebate code"),
#         help_text=_("Add rebate code if you have one"),
#         blank=True,
#     )
#
#     @property
#     def profile_complete(self):
#         return (
#             self.username
#             and self.first_name
#             and self.last_name
#             and self.country
#             and self.phone
#             and self.address
#             and self.language
#         )
#
#     @cached_property
#     def contest(self):
#         # temp solution for one-competition site
#         return Contest.objects.first().slug
#
#     def __str__(self):
#         if self.last_name and self.first_name:
#             return f"{self.last_name} {self.first_name}"
#         return self.email


# TODO: move to user.py
class Participant(User):
    class Meta:
        proxy = True
        verbose_name = _("Participant")
        verbose_name_plural = _("Participants")

    @cached_property
    def entries_stats(self):
        entries = (
            self.entries.values("is_paid", "is_received")
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


class Style(models.Model):
    name = models.CharField(max_length=50, verbose_name=_("Name"))
    slug = models.SlugField(
        unique=True,
        blank=True,
        help_text=_(
            "will be used in contest URL, can be derrived automatically from titile"
        ),
    )
    show = models.BooleanField(
        default=True, verbose_name=_("Allow to use this category in competitions")
    )
    extra_info_is_required = models.BooleanField(
        default=False, verbose_name=_("Require extra information for entries?")
    )
    extra_info_hint = models.CharField(
        max_length=255,
        verbose_name=_("Required information hint"),
        help_text=_(
            "This will instruct the participants what information they need to provide for an entry."
            "</br>Fill only if you require extra information for entries"
        ),
        blank=True,
    )
    extra_info_hint_pl = models.CharField(
        max_length=255,
        verbose_name=_("Required information hint in Polish"),
        help_text=_(
            "This will instruct the participants what information they need to provide for an entry."
            "</br>Fill only if you require extra information for entries"
        ),
        blank=True,
    )

    description = models.TextField(
        blank=False, null=False, verbose_name=_("Description in english")
    )
    description_pl = models.TextField(
        null=True, verbose_name=_("Description in polish")
    )

    # managers
    objects = StyleManager()

    # audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name="created_styles",
        editable=False,
        null=True,
    )
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name="modified_styles",
        editable=False,
        null=True,
    )

    class Meta:
        verbose_name = _("style")
        verbose_name_plural = _("styles")

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.slug,)

    def clean(self):
        if self.extra_info_is_required and self.extra_info_hint == "":
            raise ValidationError(
                _(
                    "If you require extra information from participants, provide them with a hint!"
                )
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            if Style.objects.filter(slug=self.slug).exists():
                self.slug = slugify(
                    self.name + "-" + str(Style.objects.latest("id").id)
                )

        super(Style, self).save(*args, **kwargs)


class Contest(models.Model):
    class Meta:
        verbose_name = _("contest")
        verbose_name_plural = _("contests")
        ordering = ("-judging_date_from", "-delivery_date_to")

    title = models.CharField(_("title"), max_length=255, blank=False, null=False)
    slug = models.SlugField(
        unique=True,
        blank=True,
        help_text=_(
            "will be used in contest URL, can be derrived automatically from titile"
        ),
        allow_unicode=True,
    )
    description = models.TextField(blank=False, null=False)
    description_pl = models.TextField(
        null=True, verbose_name=_("Description in polish")
    )
    rules = models.TextField(blank=True, verbose_name=_("Rules"))
    rules_pl = models.TextField(blank=True, verbose_name=_("Rules in polish"))
    logo = models.ImageField(blank=True, null=True)
    entry_fee_amount = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Entry fee amount")
    )
    entry_fee_currency = models.CharField(
        max_length=3, verbose_name=_("Fee currency code")
    )
    payment_methods = models.ManyToManyField(
        "PaymentMethod",
        verbose_name=_("Allowed payment methods"),
        related_name="contests",
    )
    payment_transfer_info = models.TextField(
        blank=True,
        verbose_name=_("Transfer payment instructions"),
        help_text=_("Mandatory if contest allows transfer payment method."),
    )
    discount_rate = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        verbose_name=_("Discount rate with promo code (in %)"),
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        default=0,
    )
    entry_global_limit = models.SmallIntegerField(
        verbose_name=_("Limit of entries in the contest"),
        help_text=_("Leave blank if no limit should be applied"),
        blank=True,
        null=True,
    )
    entry_user_limit = models.SmallIntegerField(
        verbose_name=_("Limit of entries per participant"),
        help_text=_("Leave blank if no limit should be applied"),
        blank=True,
        null=True,
    )
    delivery_address = models.TextField(
        blank=False, null=False, verbose_name=_("Delivery address")
    )
    judge_registration_date_from = models.DateField(
        blank=True, null=True, verbose_name=_("Judge registration from")
    )
    judge_registration_date_to = models.DateField(
        blank=True, null=True, verbose_name=_("to")
    )
    registration_date_from = models.DateField(
        blank=True, null=True, verbose_name=_("Entry registration from")
    )
    registration_date_to = models.DateField(blank=True, null=True, verbose_name=_("to"))
    delivery_date_from = models.DateField(
        blank=True, null=True, verbose_name=_("Delivery from")
    )
    delivery_date_to = models.DateField(blank=True, null=True, verbose_name=_("to"))
    judging_date_from = models.DateField(
        blank=True, null=True, verbose_name=_("Judging sessions from")
    )
    judging_date_to = models.DateField(blank=True, null=True, verbose_name=_("to"))

    competition_is_published = models.BooleanField(
        default=False,
        help_text=_("Ignores auto-publish date"),
        verbose_name=_("Competition page is published"),
    )
    competition_autopublish_datetime = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_(
            "Fill only if you want the competition page to be published automatically at that time"
        ),
        verbose_name=_("When to publish competition page automatically"),
    )
    result_is_published = models.BooleanField(
        default=False,
        help_text=_("Ignores auto-publish date"),
        verbose_name=_("Competition results are published"),
    )
    result_autopublish_datetime = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_(
            "Fill only if you want the competition <b>results</b> to be published automatically at that time"
        ),
        verbose_name=_("When to publish results automatically"),
    )

    styles = models.ManyToManyField(
        Style, through="Category", through_fields=("contest", "style")
    )

    is_judging_eliminations = models.BooleanField(
        default=False, verbose_name=_("Enable judges to judge elimination round.")
    )

    is_judging_finals = models.BooleanField(
        default=False, verbose_name=_("Enable judges to judge final round.")
    )
    is_judging_bos = models.BooleanField(
        default=False, verbose_name=_("Enable judges to judge Best Of Show.")
    )
    bos_entry = models.ForeignKey(
        "Entry",
        verbose_name=_("Best Of Show winner"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    # audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name="created_contests",
        editable=False,
        null=True,
    )
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name="modified_contests",
        editable=False,
        null=True,
    )

    # managers
    objects = ContestManager()
    published = PublishedContestManager()
    registrable = RegistrableContestManager()

    @cached_property
    def is_registrable(self):
        return (
            self.competition_is_published
            and self.registration_date_from <= date.today() <= self.registration_date_to
            and (self.entry_global_limit is None or self.global_limit_left)
        )

    @cached_property
    def can_judges_register(self):
        today = date.today()

        if (
            self.judge_registration_date_from
            and today < self.judge_registration_date_from
        ):
            return False

        if self.judge_registration_date_to and today > self.judge_registration_date_to:
            return False

        return True

    @cached_property
    def show_results(self):
        return self.result_is_published or (
            self.result_autopublish_datetime
            and self.result_autopublish_datetime <= datetime.now()
        )

    @cached_property
    def global_limit_left(self):
        if self.entry_global_limit is None:
            return None
        return max(
            0,
            self.entry_global_limit - Entry.objects.filter(category__contest=self)
            # .filter(is_paid=True)
            .count(),
        )

    def user_limit_left(self, user):
        if self.entry_user_limit is None:
            return None
        return max(
            0,
            self.entry_user_limit
            - Entry.objects.filter(category__contest=self).filter(brewer=user).count(),
        )

    def natural_key(self):
        return (self.slug,)

    def clean(self):
        if self._state.adding:
            return super().clean()
        transfer_method = PaymentMethod.objects.filter(code="transfer")
        if (
            transfer_method.exists()
            and transfer_method.first() in self.payment_methods.all()
            and not self.payment_transfer_info.strip()
        ):
            raise ValidationError(
                _(
                    "You have chosen to allow transfer payments. You need to provide payment info!"
                )
            )
        super().clean()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
            if Contest.objects.filter(slug=self.slug).exists():
                self.slug = slugify(
                    self.title + "-" + str(Contest.objects.latest("id").id),
                    allow_unicode=True,
                )

        super(Contest, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("contest:contest_detail", kwargs={"slug": self.slug})


class Category(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid1)
    contest = models.ForeignKey(
        Contest, on_delete=models.CASCADE, related_name="categories"
    )
    style = models.ForeignKey(
        Style,
        on_delete=models.CASCADE,
        related_name="categories",
        limit_choices_to={"show": True},
    )
    entries_limit = models.IntegerField(
        verbose_name=_("Entries limit per user"),
        default=1,
        validators=[MinValueValidator(1)],
    )
    # audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name="created_categories",
        editable=False,
        null=True,
    )
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name="modified_categories",
        editable=False,
        null=True,
    )
    objects = CategoryManager()

    class Meta:
        verbose_name = _("category")
        verbose_name_plural = _("categories")
        ordering = ["contest__title", "style__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["style", "contest"], name="unique_contest_style"
            )
        ]

    def __str__(self):
        return f"{self.style.name}"

    @cached_property
    def is_final_round_done(self):
        # number of assigned places in finals (up to 3)
        entries_with_place = self.entries.filter(place__gt=0).count()
        if entries_with_place == 3:
            return True
        # if not 3, check if there were sufficient entries in finals
        entries_in_final = len(self.entries_in_final)
        # print(self, entries_in_final)
        # no final round
        if entries_in_final == 0:
            return True

        # all entries in final got their place
        return entries_in_final == entries_with_place

    @cached_property
    def entries_in_final(self):
        return [entry.id for entry in self.entries.all() if entry.in_final_round]


class Entry(models.Model):
    class SweetnessLevel(models.TextChoices):
        DRY = "dry", _("Dry")
        MEDIUM = "medium", _("Medium")
        SWEET = "sweet", _("Sweet")

    class CarbonationLevel(models.TextChoices):
        STILL = "still", _("Still")
        PETILLANT = "petillant", _("Petillant")
        SPARKLING = "sparkling", _("Sparkling")

    id = models.UUIDField(primary_key=True, editable=False, default=uuid1)
    code = models.IntegerField(
        verbose_name=_("code"), default=code_generator, editable=False
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="entries",
        verbose_name=_("Category"),
    )
    brewer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="entries", editable=False
    )
    name = models.CharField(max_length=50, verbose_name=_("Name"))
    sweetness = models.CharField(
        max_length=10, choices=SweetnessLevel.choices, verbose_name=_("Sweetness")
    )
    carbonation = models.CharField(
        max_length=10, choices=CarbonationLevel.choices, verbose_name=_("Carbonation")
    )
    extra_info = models.CharField(
        max_length=1000, blank=True, verbose_name=_("Ingredients")
    )
    alcohol_content = models.DecimalField(
        blank=True,
        null=True,
        verbose_name=_("Alcohol content (ABV)"),
        max_digits=4,
        decimal_places=2,
    )
    place = models.PositiveIntegerField(verbose_name=_("Place"), default=0)
    is_paid = models.BooleanField(
        default=False, verbose_name=_("Is paid"), editable=False
    )
    is_received = models.BooleanField(
        default=False, verbose_name=_("Is received"), editable=False
    )
    modified_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        verbose_name = _("entry")
        verbose_name_plural = _("entries")
        ordering = [
            "category__contest__title",
            "category__style__name",
            "brewer",
            "name",
        ]

    def __str__(self):
        return str(self.code)

    def clean(self, **kwargs):
        logger.debug("Entry.clean() ==================================================")
        # bypass checks for admins
        if getattr(self, "_admin_skip_validation", False):
            return

        if self.category.style.extra_info_is_required and self.extra_info == "":
            raise ValidationError(
                _(f'Providing "{self.category.style.extra_info_hint}" is mandatory!')
            )

        if Entry.objects.filter(pk=self.id).exists():
            logger.debug("Entry.clean(): (pk=self.id).exists()")
            # update
            old = Entry.objects.get(pk=self.pk).__dict__
            altered_fields = [
                key for key, value in self.__dict__.items() if value != old.get(key)
            ]
            altered_fields.remove("_state")

            logger.debug("Entry.clean(): altered_fields={}".format(altered_fields))
            logger.debug("Entry.clean(): can_be_edited={}".format(self.can_be_edited()))
            if not self.can_be_edited():

                # check if we're updating only place attribute
                allowed_modifications = ["place"]
                changes_allowed = (
                    all([field in allowed_modifications for field in altered_fields])
                    and len(altered_fields) == len(allowed_modifications)
                ) or len(altered_fields) == 0
                if not changes_allowed:
                    raise ValidationError(_("Entry cannot be edited anymore!"))

            extra = 0

            # validate category limit if category changed
            if (
                "category_id" in altered_fields
                and self.category.entries_limit
                <= Entry.objects.filter(category=self.category)
                .filter(brewer=self.brewer)
                .count()
            ):
                raise ValidationError(
                    _("Cannot change category due to target category limit")
                )
        else:
            # insert
            extra = 1

        # validate limits
        if extra:
            # verify category limit
            if (
                self.category.entries_limit
                < Entry.objects.filter(category=self.category)
                .filter(brewer=self.brewer)
                .count()
                + extra
            ):
                raise ValidationError(
                    _(
                        f"You have reached entry limit for this category ({self.category.entries_limit})!"
                    )
                )

            # verify global limit
            if (
                self.category.contest.entry_global_limit is not None
                and self.category.contest.global_limit_left <= 0
            ):
                raise ValidationError(
                    _(
                        "This contest has reached maximum number of entries, no more entries can be registered."
                    )
                )

            # verify user limit
            limit_left = self.category.contest.user_limit_left(self.brewer)
            if limit_left is not None and limit_left <= 0:
                raise ValidationError(
                    _(
                        "You have reached maximum number of entries per user in this competition."
                    )
                )

    def delete(self, using=None, keep_parents=False):
        if not self.can_be_deleted():
            raise ValidationError(
                _("Entries that has been paid or received cannot be deleted!")
            )
        super().delete(using, keep_parents)

    def can_be_deleted(self):
        return not self.is_paid and not self.is_received

    def can_be_edited(self):
        # return not self.is_received
        return self.category.contest.registration_date_to >= date.today()

    @cached_property
    def scoresheet(self):
        if self.scoresheets.count() == 1:
            return self.scoresheets.first()
        return None

    @cached_property
    def in_final_round(self):
        if self.scoresheets.count() == 1:
            return self.scoresheets.first().final_round
        return False


class EntriesPackage(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid1)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="packages")
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name="+")
    entries = models.ManyToManyField(Entry, related_name="packages")

    def entries_codes_as_li(self):
        return "".join(
            [f"<li>{entry.code}</li>" for entry in self.entries.order_by("code").all()]
        )


class PaymentMethod(models.Model):
    class Meta:
        verbose_name = _("Payment Method")
        verbose_name_plural = _("Payment Methods")

    id = models.UUIDField(primary_key=True, editable=False, default=uuid1)
    logo = models.ImageField(
        blank=True, null=True, help_text=_("Displayed at payment method selection page")
    )
    name = models.CharField(max_length=50, verbose_name=_("Name"))
    name_pl = models.CharField(max_length=50, verbose_name=_("Polish name"))
    code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name=_("Method code"),
        help_text=_("Code is used by the software, do not change!"),
    )

    # managers
    objects = PaymentMethodManager()

    def __str__(self):
        return self.code

    def natural_key(self):
        return self.code


class Payment(models.Model):
    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("payment")
        verbose_name_plural = _("payments")

    class PaymentStatus(models.TextChoices):
        CREATED = "created", _("Created")
        CANCELED = "canceled", _("Canceled")
        OK = "ok", _("OK")
        FAILED = "failed", _("Failed")
        AWAITING = "awaiting", _("Confirmation pending")

    id = models.UUIDField(primary_key=True, editable=False, default=uuid1)
    method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.DO_NOTHING,
        related_name="+",
        verbose_name=_("Method"),
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="payments", verbose_name=_("User")
    )
    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("Contest"),
    )
    entries = models.ManyToManyField(
        Entry, related_name="payments", verbose_name=_("Entries")
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Amount")
    )
    currency = models.CharField(max_length=3, verbose_name=_("Currency"))
    status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.CREATED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    code = models.CharField(max_length=50, null=True)

    # managers
    objects = DefaultManager()
    pending = PaymentManagerExcludeStatuses(
        (PaymentStatus.OK, PaymentStatus.FAILED), methods=("transfer",)
    )

    def __str__(self):
        return f"{self.user}: {self.amount} {self.currency} [{self.status}]"

    def save(self, *args, **kwargs):
        if self.status == Payment.PaymentStatus.OK and (
            self._state.adding
            or not self._state.adding
            and Payment.objects.get(pk=self.pk).status != self.status
        ):
            self.entries.update(is_paid=True)
            mail_entry_status_change(self.entries.all(), "PAID")

        super().save(*args, **kwargs)


class ScoreSheet(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid1)
    entry = models.ForeignKey(
        Entry,
        on_delete=models.CASCADE,
        related_name="scoresheets",
        verbose_name=_("Entry"),
    )
    # TODO refactor - final_round should be in Entry
    final_round = models.BooleanField(verbose_name=_("Final round"), default=False)

    appearance = models.TextField(verbose_name=_("Appearance"), blank=True)
    appearance_score = models.PositiveIntegerField(
        verbose_name=_("Appearance score"),
        validators=(MaxValueValidator(12),),
    )
    aroma = models.TextField(verbose_name=_("Aroma"), blank=True)
    aroma_score = models.PositiveIntegerField(
        verbose_name=_("Aroma score"), validators=(MaxValueValidator(30),)
    )
    flavor = models.TextField(verbose_name=_("Flavor and body"), blank=True)
    flavor_score = models.PositiveIntegerField(
        verbose_name=_("Flavor and body score"), validators=(MaxValueValidator(32),)
    )
    finish = models.TextField(verbose_name=_("Finish"), blank=True)
    finish_score = models.PositiveIntegerField(
        verbose_name=_("Finish score"), validators=(MaxValueValidator(14),)
    )
    overall = models.TextField(verbose_name=_("Overall impression"), blank=True)
    overall_score = models.PositiveIntegerField(
        verbose_name=_("Overal impression score"), validators=(MaxValueValidator(12),)
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Score Sheet")
        verbose_name_plural = _("Score Sheets")

    def __str__(self):
        return f"{self.entry.code}"

    @cached_property
    def total_points(self):
        return (
            self.aroma_score
            + self.flavor_score
            + self.appearance_score
            + self.finish_score
            + self.overall_score
        )


class RebateCode(models.Model):
    class Meta:
        verbose_name = _("Rebate Code")
        verbose_name_plural = _("Rebate Codes")

    id = models.UUIDField(primary_key=True, default=uuid1, editable=False)
    code = models.CharField(
        max_length=10,
        unique=True,
        default=rebate_code_generator,
        editable=False,
        verbose_name=_("Code"),
    )
    is_used = models.BooleanField(default=False, verbose_name=_("Is used"))
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rebate_code",
    )

    def __str__(self):
        return self.code

    def use(self, user):
        if self.is_used and self.user != user:
            raise ValueError("This code has already been used.")
        self.user = user
        self.is_used = True
        self.save()
