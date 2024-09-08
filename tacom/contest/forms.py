from django import forms
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox
from django_countries.widgets import CountrySelectWidget
from tinymce.widgets import TinyMCE

from .models import Entry, User, EntriesPackage, Payment, PaymentMethod, ScoreSheet


class NewEntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ['name', 'extra_info']
        widgets = {
            'name': forms.TextInput(attrs={'size': 80}),
            # 'extra_info': forms.TextInput(attrs={'size': 80}),
            'extra_info': forms.Textarea(attrs={'cols': 80, 'rows': 15})
        }

    def __init__(self, *args, **kwargs):
        is_extra_mandatory = kwargs.pop('is_extra_mandatory', None)
        extra_hint = kwargs.pop('extra_hint', None)
        user = kwargs.pop('user', None)
        category = kwargs.pop('category', None)
        super().__init__(*args, **kwargs)
        if extra_hint:
            self.fields['extra_info'].label = extra_hint
        if is_extra_mandatory:
            self.fields['extra_info'].required = True
        self.instance.brewer = user
        self.instance.category = category


class EditEntryForm(NewEntryForm):
    class Meta:
        fields = ('category', 'name', 'extra_info')
        widgets = {
            'name': forms.TextInput(attrs={'size': 80}),
            'extra_info': forms.Textarea(attrs={'cols': 80, 'rows': 15})
        }
        model = Entry


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        widgets = {
            'address': forms.Textarea(attrs={'cols': 30, 'rows': 4}),
            'country': CountrySelectWidget()
        }
        fields = [
            'username',
            'first_name',
            'last_name',
            'country',
            'phone',
            'address',
            'language'
        ]

    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)


class EntryField(forms.ModelMultipleChoiceField):

    def __init__(self, queryset, **kwargs):
        self.show_entry_codes = kwargs.pop('show_entry_codes', False)
        super().__init__(queryset, **kwargs)

    def label_from_instance(self, obj):
        extra = f'<b>{obj.code}</b> - ' if self.show_entry_codes else ''
        return mark_safe(f'{extra}{obj.category.style.name} - {obj.name}')


class NewPackageForm(forms.ModelForm):
    entries = EntryField(
        queryset=Entry.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label=''
    )

    class Meta:
        model = EntriesPackage
        fields = ('entries',)

    def __init__(self, *args, **kwargs):
        queryset = kwargs.pop('entries')
        self.purpose = kwargs.pop('purpose', None)
        self.owner = kwargs.pop('owner', None)
        self.contest = kwargs.pop('contest', None)
        self.target = kwargs.pop('target', None)
        self.show_entry_codes = kwargs.pop('show_entry_codes', False)
        super().__init__(*args, **kwargs)
        self.fields['entries'].queryset = queryset
        self.fields['entries'].show_entry_codes = self.show_entry_codes
        self.options_count = queryset.count()

    def super_clean(self):
        return super().clean()

    def clean(self):
        cleaned_data = self.super_clean()
        if not cleaned_data.get('entries'):
            return cleaned_data
        for entry in cleaned_data.get('entries'):
            if self.owner != entry.brewer:
                raise ValidationError(_('Cannot add entry that does not belong to user'))
            if self.contest != entry.category.contest:
                raise ValidationError(_('Cannot add entry from another contest'))
        return cleaned_data


class NewAdminPackage(NewPackageForm):
    """
    This form allows selection of not-owned entries - for contest staff views
    """

    def clean(self):
        cleaned_data = super().super_clean()
        if not cleaned_data.get('entries'):
            return cleaned_data
        for entry in cleaned_data.get('entries'):
            if self.contest != entry.category.contest:
                raise ValidationError(_('Cannot add entry from another contest'))
        return cleaned_data


class ImageChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.logo:
            return mark_safe(f'<span><img src="{obj.logo.url}" width="300"/> {obj.name} / {obj.name_pl}</span>')
        return f'{obj.name} / {obj.name_pl}'


class NewPaymentForm(forms.ModelForm):
    method = ImageChoiceField(
        queryset=PaymentMethod.objects.all(),
        widget=forms.RadioSelect,
        label=''
    )

    class Meta:
        model = Payment
        fields = ('method',)
        # widgets = {'method': TableRadioImageSelect}

    def __init__(self, *args, **kwargs):
        self.contest = kwargs.pop('contest')
        super().__init__(*args, **kwargs)
        self.fields['method'].queryset = self.contest.payment_methods

    def clean(self):
        cleaned_data = super().clean()
        if not self.contest.payment_methods.filter(code=cleaned_data.get('method')).exists():
            raise ValidationError(_('This method is not allowed for this contest'))
        return cleaned_data


class DeletePaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = '__all__'


class EnhancedForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.head_info = kwargs.pop('head_info', None)
        self.return_url = kwargs.pop('return_url', None)
        super().__init__(*args, **kwargs)


class FakePaymentForm(EnhancedForm):
    payment_successful = forms.ChoiceField(
        widget=forms.RadioSelect,
        label=_('Is payment successful?'),
        choices=(
            ('yes', _('Yes')),
            ('no', _('No'))
        )
    )


class BlankForm(EnhancedForm):
    pass


class ScoreSheetForm(forms.ModelForm):
    class Meta:
        model = ScoreSheet
        fields = ['has_medal', 'description']
        widgets = {
            'description': TinyMCE(attrs={'cols': 120, 'rows': 50})
        }
