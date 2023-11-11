from django import forms
from django.core.exceptions import ValidationError

from .models import Entry, UserDetails


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


class UserDetailsForm(forms.ModelForm):
    class Meta:
        model = UserDetails
        exclude = ('id', 'user')
