from datetime import date
from uuid import uuid1

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .managers import StyleManager, ContestManager, RegistrableContestManager, PublishedContestManager, CategoryManager


class Style(models.Model):
    name = models.CharField(max_length=50)
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
    entry_fee_amount = models.DecimalField(max_digits=10, decimal_places=2)
    entry_fee_currency = models.CharField(max_length=3, verbose_name=_('Fee currency code'))
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
            self.entry_global_limit - Entry.objects.filter(category__contest=self).filter(is_paid=True).count()
        )

    class Meta:
        verbose_name = _('contest')
        verbose_name_plural = _('contests')
        ordering = ('-judging_date_from', '-delivery_date_to')

    def natural_key(self):
        return self.slug

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


class Entry(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid1)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='entries')
    brewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='entries')
    name = models.CharField(max_length=50)
    extra_info = models.CharField(max_length=25, blank=True, verbose_name=_('Additional information'))
    is_paid = models.BooleanField(default=False)
    is_received = models.BooleanField(default=False)
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
                raise ValidationError(_(f'You have reached entry limit for this category ({self.category.entries_limit})! '
                                        f'No more entries in this category can be added.'))

            # verify global limit
            if self.category.contest.entry_global_limit is not None and self.category.contest.global_limit_left <= 0:
                raise ValidationError(
                    _('This contest has reached maximum number of entries, no more entries can be registered.')
                )

    def delete(self, using=None, keep_parents=False):
        if not self.can_be_deleted():
            raise ValidationError(_('Entries that has been paid or received cannot be deleted!'))
        super().delete(using, keep_parents)

    def can_be_deleted(self):
        return not self.is_paid and not self.is_received

    def can_be_edited(self):
        return not self.is_received
