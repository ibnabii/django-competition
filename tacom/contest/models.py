from datetime import date
from uuid import uuid1

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from django_countries.fields import CountryField

from .managers import StyleManager, ContestManager, RegistrableContestManager, PublishedContestManager, CategoryManager
from .utils import mail_entry_status_change


class User(AbstractUser):
    class Meta:
        db_table = 'auth_user'

    class JudgingLanguage(models.TextChoices):
        polish = 'pl', _('Polish')
        english = 'en', _('English')

    country = CountryField(verbose_name=_('Country'), blank=True)
    phone = models.CharField(
        max_length=15,
        verbose_name=_('Phone number'),
        blank=True
    )
    address = models.CharField(max_length=200, blank=True)
    language = models.CharField(
        verbose_name=_('I would like to get feedback on my meads in'),
        choices=JudgingLanguage.choices,
        blank=True,
        max_length=2
    )

    @property
    def profile_complete(self):
        return (
            self.username and self.first_name and self.last_name and self.country and self.phone
            and self.address and self.language
        )

    @property
    def contest(self):
        # temp solution for one-competition site
        return Contest.objects.first().slug

    def __str__(self):
        if self.last_name and self.first_name:
            return f'{self.last_name} {self.first_name}'
        return self.email


class Participant(User):
    class Meta:
        proxy = True
        verbose_name = _('Participant')
        verbose_name_plural = _('Participants')

    @cached_property
    def entries_stats(self):
        entries = (
            self.entries
            .values('is_paid', 'is_received')
            # .annotate(paid=models.Count('is_paid'), received=models.Count('is_received'))
            .annotate(count=models.Count('is_paid'))
        )
        return {
            'total': entries.aggregate(total=models.Sum('count')).get('total') or 0,
            'paid': entries.filter(is_paid=True).count(),
            'received': entries.filter(is_received=True).count()
        }

    @property
    def entries_total(self):
        return self.entries_stats.get('total')
    entries_total.fget.short_description = _('Registered')

    @property
    def entries_paid(self):
        return self.entries_stats.get('paid')
    entries_paid.fget.short_description = _('Paid')

    @property
    def entries_received(self):
        return self.entries_stats.get('received')
    entries_received.fget.short_description = _('Received')


class Style(models.Model):
    name = models.CharField(max_length=50, verbose_name=_('Name'))
    slug = models.SlugField(
        unique=True,
        blank=True,
        help_text=_('will be used in contest URL, can be derrived automatically from titile')
    )
    show = models.BooleanField(default=True, verbose_name=_('Allow to use this category in competitions'))
    extra_info_is_required = models.BooleanField(
        default=False,
        verbose_name=_('Require extra information for entries?')
    )
    extra_info_hint = models.CharField(
        max_length=255,
        verbose_name=_('Required information hint'),
        help_text=_('This will instruct the participants what information they need to provide for an entry.'
                    '</br>Fill only if you require extra information for entries'),
        blank=True
    )
    description = models.TextField(blank=False, null=False)
    description_pl = models.TextField(null=True, verbose_name=_('Description in polish'))

    # managers
    objects = StyleManager()

    # audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name='created_styles',
        editable=False,
        null=True
    )
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name='modified_styles',
        editable=False,
        null=True
    )

    class Meta:
        verbose_name = _('style')
        verbose_name_plural = _('styles')

    def __str__(self):
        return self.name

    def natural_key(self):
        return self.slug

    def clean(self):
        if self.extra_info_is_required and self.extra_info_hint == '':
            raise ValidationError(_('If you require extra information from participants, provide them with a hint!'))

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            if Style.objects.filter(slug=self.slug).exists():
                self.slug = slugify(self.name + '-' + str(Style.objects.latest('id').id))

        super(Style, self).save(*args, **kwargs)


class Contest(models.Model):
    title = models.CharField(_('title'), max_length=255, blank=False, null=False)
    slug = models.SlugField(
        unique=True,
        blank=True,
        help_text=_('will be used in contest URL, can be derrived automatically from titile')
    )
    description = models.TextField(blank=False, null=False)
    description_pl = models.TextField(null=True, verbose_name=_('Description in polish'))
    logo = models.ImageField(blank=True, null=True)
    entry_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Entry fee amount'))
    entry_fee_currency = models.CharField(max_length=3, verbose_name=_('Fee currency code'))
    payment_methods = models.ManyToManyField('PaymentMethod',
                                             verbose_name=_('Allowed payment methods'),
                                             related_name='contests')
    payment_transfer_info = models.TextField(
        blank=True,
        verbose_name=_('Transfer payment instructions'),
        help_text=_('Mandatory if contest allows transfer payment method.')
    )
    entry_global_limit = models.SmallIntegerField(
        verbose_name=_('Limit of entries in the contest'),
        help_text=_('Leave blank if no limit should be applied'),
        blank=True,
        null=True
    )
    entry_user_limit = models.SmallIntegerField(
        verbose_name=_('Limit of entries per participant'),
        help_text=_('Leave blank if no limit should be applied'),
        blank=True,
        null=True
    )
    delivery_address = models.TextField(blank=False, null=False, verbose_name=_('Delivery address'))
    registration_date_from = models.DateField(blank=True, null=True, verbose_name=_('Entry registration from'))
    registration_date_to = models.DateField(blank=True, null=True, verbose_name=_('to'))
    delivery_date_from = models.DateField(blank=True, null=True, verbose_name=_('Delivery from'))
    delivery_date_to = models.DateField(blank=True, null=True, verbose_name=_('to'))
    judging_date_from = models.DateField(blank=True, null=True, verbose_name=_('Judging sessions from'))
    judging_date_to = models.DateField(blank=True, null=True, verbose_name=_('to'))

    competition_is_published = models.BooleanField(
        default=False,
        help_text=_('Ignores auto-publish date'),
        verbose_name=_('Competition page is published')
    )
    competition_autopublish_datetime = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_('Fill only if you want the competition page to be published automatically at that time'),
        verbose_name=_('When to publish competition page automatically')
    )
    result_is_published = models.BooleanField(
        default=False,
        help_text=_('Ignores auto-publish date'),
        verbose_name=_('Competition results are published')
    )
    result_autopublish_datetime = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_('Fill only if you want the competition <b>results</b> to be published automatically at that time'),
        verbose_name=_('When to publish results automatically')
    )

    styles = models.ManyToManyField(Style, through='Category', through_fields=('contest', 'style'))

    # audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name='created_contests',
        editable=False,
        null=True
    )
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name='modified_contests',
        editable=False,
        null=True
    )

    # managers
    objects = ContestManager()
    published = PublishedContestManager()
    registrable = RegistrableContestManager()

    def is_registrable(self):
        return (self.competition_is_published
                and self.registration_date_from <= date.today() <= self.registration_date_to
                and (self.entry_global_limit is None or self.global_limit_left)
                )

    @cached_property
    def global_limit_left(self):
        if self.entry_global_limit is None:
            return None
        return max(
            0,
            self.entry_global_limit - Entry.objects
            .filter(category__contest=self)
            # .filter(is_paid=True)
            .count()
        )

    def user_limit_left(self, user):
        if self.entry_user_limit is None:
            return None
        return max(
            0,
            self.entry_user_limit - Entry.objects.filter(category__contest=self).filter(brewer=user).count()
        )

    class Meta:
        verbose_name = _('contest')
        verbose_name_plural = _('contests')
        ordering = ('-judging_date_from', '-delivery_date_to')

    def natural_key(self):
        return self.slug

    def clean(self):
        if (PaymentMethod.objects.get(code='transfer') in self.payment_methods.all()
                and not self.payment_transfer_info.strip()):
            raise ValidationError(_('You have chosen to allow transfer payments. You need to provide payment info!'))
        super().clean()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            if Contest.objects.filter(slug=self.slug).exists():
                self.slug = slugify(self.title + '-' + str(Contest.objects.latest('id').id))

        super(Contest, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('contest:contest_detail', kwargs={"slug": self.slug})


class Category(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid1)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='categories')
    style = models.ForeignKey(
        Style,
        on_delete=models.CASCADE,
        related_name='categories',
        limit_choices_to={"show": True}
    )
    entries_limit = models.IntegerField(
        verbose_name=_('Entries limit per user'),
        default=1,
        validators=[MinValueValidator(1)]
    )
    # audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name='created_categories',
        editable=False,
        null=True
    )
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name='modified_categories',
        editable=False,
        null=True
    )
    objects = CategoryManager()

    class Meta:
        verbose_name = _('category')
        verbose_name_plural = _('categories')
        ordering = ['contest__title', 'style__name']
        constraints = [models.UniqueConstraint(fields=['style', 'contest'], name='unique_contest_style')]

    def __str__(self):
        return f'{self.contest.title} - {self.style.name}'


def code_generator():
    # for migration only:
    # return 0
    maximum_code = Entry.objects.aggregate(models.Max('code'))['code__max']
    if maximum_code:
        return int(maximum_code) + 1
    return 1000


class Entry(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid1)
    code = models.IntegerField(verbose_name=_('code'), default=code_generator)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='entries')
    brewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='entries')
    name = models.CharField(max_length=50, verbose_name=_('Name'))
    extra_info = models.CharField(max_length=1000, blank=True, verbose_name=_('Additional information'))
    is_paid = models.BooleanField(default=False, verbose_name=_('Is paid'))
    is_received = models.BooleanField(default=False, verbose_name=_('Is received'))
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('entry')
        verbose_name_plural = _('entries')
        ordering = ['category__contest__title', 'category__style__name', 'brewer', 'name']

    def __str__(self):
        return str(self.id)

    def clean(self):
        if self.category.style.extra_info_is_required and self.extra_info == '':
            raise ValidationError(_(f'Providing "{self.category.style.extra_info_hint}" is mandatory!'))

        if Entry.objects.filter(pk=self.id).exists():
            # update
            if not self.can_be_edited():
                raise ValidationError(_('Entries that have been received cannot be edited!'))
            extra = 0
        else:
            # insert
            extra = 1

        # validate limits
        if extra:
            # verify category limit
            if (self.category.entries_limit
                    <
                    Entry.objects.filter(category=self.category).filter(brewer=self.brewer).count() + extra):
                raise ValidationError(_(
                    f'You have reached entry limit for this category ({self.category.entries_limit})!'
                    f'No more entries in this category can be added.'))

            # verify global limit
            if self.category.contest.entry_global_limit is not None and self.category.contest.global_limit_left <= 0:
                raise ValidationError(
                    _('This contest has reached maximum number of entries, no more entries can be registered.')
                )

            # verify user limit
            limit_left = self.category.contest.user_limit_left(self.brewer)
            if limit_left is not None and limit_left <= 0:
                raise ValidationError(
                    _('You have reached maximum number of entries per user in this competition.')
                )

    def delete(self, using=None, keep_parents=False):
        if not self.can_be_deleted():
            raise ValidationError(_('Entries that has been paid or received cannot be deleted!'))
        super().delete(using, keep_parents)

    def can_be_deleted(self):
        return not self.is_paid and not self.is_received

    def can_be_edited(self):
        return not self.is_received


class EntriesPackage(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid1)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='packages')
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='+')
    entries = models.ManyToManyField(Entry, related_name='packages')

    def entries_codes_as_li(self):
        return ''.join([f'<li>{entry.code}</li>' for entry in self.entries.order_by('code').all()])


class PaymentMethod(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid1)
    logo = models.ImageField(blank=True, null=True, help_text=_('Displayed at payment method selection page'))
    name = models.CharField(max_length=50, verbose_name=_('Name'))
    name_pl = models.CharField(max_length=50, verbose_name=_('Polish name'))
    code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name=_('Method code'),
        help_text=_('Code is used by the software, do not change!')
    )

    def __str__(self):
        return self.code


class Payment(models.Model):
    class Meta:
        ordering = ('-created_at',)
        verbose_name = _('payment')
        verbose_name_plural = _('payments')

    class PaymentStatus(models.TextChoices):
        CREATED = 'created', _('Created')
        CANCELED = 'canceled', _('Canceled')
        OK = 'ok', _('OK')
        FAILED = 'failed', _('Failed')
        AWAITING = 'awaiting', _('Confirmation pending')

    id = models.UUIDField(primary_key=True, editable=False, default=uuid1)
    method = models.ForeignKey(PaymentMethod, on_delete=models.DO_NOTHING, related_name='+', verbose_name=_('Method'))
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments', verbose_name=_('User'))
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='payments', verbose_name=_('Contest'))
    entries = models.ManyToManyField(Entry, related_name='payments', verbose_name=_('Entries'))
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Amount'))
    currency = models.CharField(max_length=3, verbose_name=_('Currency'))
    status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.CREATED)
    created_at = models.DateTimeField(auto_now_add=True)
    code = models.CharField(max_length=50, null=True)

    def __str__(self):
        return f'{self.user}: {self.amount} {self.currency} [{self.status}]'

    def save(self, *args, **kwargs):
        if (self.status == Payment.PaymentStatus.OK
                and (self._state.adding
                     or not self._state.adding and Payment.objects.get(pk=self.pk).status != self.status
                )):
            self.entries.update(is_paid=True)
            mail_entry_status_change(self.entries.all(), 'PAID')

        super().save(*args, **kwargs)


