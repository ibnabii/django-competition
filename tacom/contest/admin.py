from django.contrib import admin
from django.db.models import TextField
from django.utils.translation import gettext_lazy as _
from tinymce.widgets import TinyMCE

from .models import Contest

class ContestAdmin(admin.ModelAdmin):
    model = Contest
    readonly_fields = [
        'created_at',
        'created_by',
        'modified_at',
        'modified_by'
    ]
    formfield_overrides = {
        TextField: {'widget': TinyMCE(attrs={'cols': 80, 'rows': 30})},
    }
    fieldsets = [
        (
            None,
            {
                'fields': ['title', 'slug']
            }
        ),
        (
            _('Description'),
            {
                'classes': ['collapse'],
                'fields': ['description'],
            }
        ),
        (
            _('Dates'),
            {
                'fields': [
                    ('registration_date_from', 'registration_date_to'),
                    ('delivery_date_from', 'delivery_date_to'),
                    ('judging_date_from', 'judging_date_to'),
                ]
            }
        ),
        (
            _('Publish competition page'),
            {
                'fields': [
                    'competition_is_published',
                    'competition_autopublish_datetime',
                ]
            }
        ),
        (
            _('Publish competition results'),
            {
                'fields': [
                    'result_is_published',
                    'result_autopublish_datetime'
                ]
            }
        ),
        (
            _('Audit'),
            {
                'fields': [('created_at', 'created_by'), ('modified_at', 'modified_by')]
            }
        ),
    ]
    def save_model(self, request, obj, form, change):
        obj.modified_by = request.user
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

admin.site.register(Contest, ContestAdmin)
