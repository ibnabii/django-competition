from allauth.account.forms import SignupForm
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from django_countries.widgets import CountrySelectWidget
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox

from .models import (
    Contest,
    EntriesPackage,
    Entry,
    Payment,
    PaymentMethod,
    RebateCode,
    ScoreSheet,
    User,
)


class NewEntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        # fields = ['name', 'extra_info']
        exclude = ("category", "place")
        widgets = {
            "name": forms.TextInput(attrs={"size": 80}),
            # 'extra_info': forms.TextInput(attrs={'size': 80}),
            "extra_info": forms.Textarea(attrs={"cols": 80, "rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        is_extra_mandatory = kwargs.pop("is_extra_mandatory", None)
        extra_hint = kwargs.pop("extra_hint", None)
        user = kwargs.pop("user", None)
        category = kwargs.pop("category", None)
        return_url = kwargs.pop("return_url", None)
        super().__init__(*args, **kwargs)
        if extra_hint:
            self.fields["extra_info"].label = extra_hint
        if is_extra_mandatory:
            self.fields["extra_info"].required = True
        self.instance.brewer = user
        self.instance.category = category

        if return_url:
            self.return_url = return_url


class EditEntryForm(NewEntryForm):
    class Meta:
        exclude = ("place",)
        widgets = {
            "name": forms.TextInput(attrs={"size": 80}),
            "extra_info": forms.Textarea(attrs={"cols": 80, "rows": 5}),
        }
        model = Entry


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        widgets = {
            "address": forms.Textarea(attrs={"cols": 30, "rows": 4}),
            "country": CountrySelectWidget(),
        }
        fields = [
            "username",
            "first_name",
            "last_name",
            "country",
            "phone",
            "address",
            "language",
            "rebate_code_text",
        ]

    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)

    def clean_rebate_code_text(self):
        rebate_code_text = self.cleaned_data.get("rebate_code_text")

        if rebate_code_text:
            try:
                # Try to find a rebate code with the provided text
                rebate_code = RebateCode.objects.get(code=rebate_code_text)
                if rebate_code.is_used and rebate_code.user != self.instance:
                    raise ValidationError(_("This code has already been used."))

                # If all checks pass, mark the rebate code as used and assign it to the user
                rebate_code.use(self.instance)  # `self.instance` is the current User

            except RebateCode.DoesNotExist:
                raise ValidationError(_("Wrong code"))

        return rebate_code_text


class EntryField(forms.ModelMultipleChoiceField):

    def __init__(self, queryset, **kwargs):
        self.show_entry_codes = kwargs.pop("show_entry_codes", False)
        super().__init__(queryset, **kwargs)

    def label_from_instance(self, obj):
        extra = f"<b>{obj.code}</b> - " if self.show_entry_codes else ""
        return mark_safe(f"{extra}{obj.category.style.name} - {obj.name}")


class NewPackageForm(forms.ModelForm):
    entries = EntryField(
        queryset=Entry.objects.all(), widget=forms.CheckboxSelectMultiple, label=""
    )

    class Meta:
        model = EntriesPackage
        fields = ("entries",)

    def __init__(self, *args, **kwargs):
        queryset = kwargs.pop("entries")
        self.purpose = kwargs.pop("purpose", None)
        self.owner = kwargs.pop("owner", None)
        self.contest = kwargs.pop("contest", None)
        self.target = kwargs.pop("target", None)
        self.show_entry_codes = kwargs.pop("show_entry_codes", False)
        super().__init__(*args, **kwargs)
        self.fields["entries"].queryset = queryset
        self.fields["entries"].show_entry_codes = self.show_entry_codes
        self.options_count = queryset.count()

    def super_clean(self):
        return super().clean()

    def clean(self):
        cleaned_data = self.super_clean()
        if not cleaned_data.get("entries"):
            return cleaned_data
        for entry in cleaned_data.get("entries"):
            if self.owner != entry.brewer:
                raise ValidationError(
                    _("Cannot add entry that does not belong to user")
                )
            if self.contest != entry.category.contest:
                raise ValidationError(_("Cannot add entry from another contest"))
        return cleaned_data


class NewAdminPackage(NewPackageForm):
    """
    This form allows selection of not-owned entries - for contest staff views
    """

    def clean(self):
        cleaned_data = super().super_clean()
        if not cleaned_data.get("entries"):
            return cleaned_data
        for entry in cleaned_data.get("entries"):
            if self.contest != entry.category.contest:
                raise ValidationError(_("Cannot add entry from another contest"))
        return cleaned_data


class ImageChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.logo:
            return mark_safe(
                f'<span><img src="{obj.logo.url}" width="300"/> {obj.name} / {obj.name_pl}</span>'
            )
        return f"{obj.name} / {obj.name_pl}"


class NewPaymentForm(forms.ModelForm):
    method = ImageChoiceField(
        queryset=PaymentMethod.objects.all(), widget=forms.RadioSelect, label=""
    )

    class Meta:
        model = Payment
        fields = ("method",)
        # widgets = {'method': TableRadioImageSelect}

    def __init__(self, *args, **kwargs):
        self.contest = kwargs.pop("contest")
        super().__init__(*args, **kwargs)
        self.fields["method"].queryset = self.contest.payment_methods

    def clean(self):
        cleaned_data = super().clean()
        if not self.contest.payment_methods.filter(
            code=cleaned_data.get("method")
        ).exists():
            raise ValidationError(_("This method is not allowed for this contest"))
        return cleaned_data


class DeletePaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = "__all__"


class EnhancedForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.head_info = kwargs.pop("head_info", None)
        self.return_url = kwargs.pop("return_url", None)
        super().__init__(*args, **kwargs)


class FakePaymentForm(EnhancedForm):
    payment_successful = forms.ChoiceField(
        widget=forms.RadioSelect,
        label=_("Is payment successful?"),
        choices=(("yes", _("Yes")), ("no", _("No"))),
    )


class BlankForm(EnhancedForm):
    pass


class ScoreSheetForm(forms.ModelForm):

    class Meta:
        model = ScoreSheet
        exclude = ["place", "entry"]
        # tinymce = TinyMCE(attrs={"cols": 120, "rows": 50})
        # widgets = {"appearance": tinymce}


class CustomSignupForm(SignupForm):
    gdpr_consent = forms.BooleanField()
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        url = reverse("contest:privacy")
        current_language = get_language()
        self.order_fields(
            ["username", "email", "password1", "password2", "gdpr_consent"]
        )
        if current_language == "pl":
            self.fields["gdpr_consent"].label = mark_safe(
                f"Wyrażam zgodę na wykorzystywanie<br/>moich danych osobowych zgodnie z<br />"
                f"<a href='{url}' target='_blank'>Polityką Prywatności</a> KMP Bartnik"
            )
        else:
            self.fields["gdpr_consent"].label = mark_safe(
                f"I accept processing of my data<br />per "
                f"KMP Bartnik's <a href='{url}' target='_blank'>Privacy Policy</a>"
            )

    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        user.gdpr_consent = self.cleaned_data["gdpr_consent"]
        user.save()
        return user


class FinalEntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            if field_name != "place":
                self.fields[field_name].widget = forms.HiddenInput()


class FinalEntryFormset(forms.BaseModelFormSet):
    def save(self, commit=True, **kwargs):
        print("FinalEntryFormset.save")
        final_judgment = kwargs.pop("final_judgment", False)
        instances = super().save(commit=False)  # Get the instances without saving them
        for instance in instances:
            if commit:
                instance.save(final_judgment=final_judgment)  # Save the instance
        return instances


FinalEntriesFormset = forms.modelformset_factory(Entry, form=FinalEntryForm, extra=0)


class ContestBestOfShowForm(forms.ModelForm):
    class Meta:
        model = Contest
        fields = ["bos_entry"]

        widgets = {
            "bos_entry": forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        candidates = kwargs.pop("candidates", None)
        super().__init__(*args, **kwargs)
        if candidates:
            self.fields["bos_entry"].queryset = candidates
