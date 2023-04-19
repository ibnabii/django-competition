from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import TextField
from django.utils.translation import gettext_lazy as _
from tinymce.widgets import TinyMCE

from .models import Contest, Style, Entry


@admin.register(Style)
class StyleAdmin(admin.ModelAdmin):
    model = Style
    formfield_overrides = {
        TextField: {'widget': TinyMCE(attrs={'cols': 80, 'rows': 30})},
    }
    readonly_fields = [
        'created_at',
        'created_by',
        'modified_at',
        'modified_by'
    ]

    def save_model(self, request, obj, form, change):
        obj.modified_by = request.user
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class CategoriesForContest(admin.TabularInline):
    model = Contest.styles.through
    extra = 0


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    # save_on_top = True
    model = Contest
    inlines = (CategoriesForContest,)
    # filter_horizontal = ('categories', )
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
        # (
        #     _('Categories'),
        #     {
        #         'classes': ['collapse'],
        #         'fields': ['styles'],
        #     }
        # ),
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


# @admin.register(Category)
# class CategoryAdmin(admin.ModelAdmin):
#     model = Category
#     readonly_fields = [
#         'created_at',
#         'created_by',
#         'modified_at',
#         'modified_by'
#     ]
#
#     def save_model(self, request, obj, form, change):
#         obj.modified_by = request.user
#         if not change:
#             obj.created_by = request.user
#         super().save_model(request, obj, form, change)

admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    readonly_fields = [
        'date_joined',
        'last_login',
    ]


    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        is_superuser = request.user.is_superuser

        form.base_fields['user_permissions'].disabled = True
        form.base_fields['is_staff'].disabled = True
        form.base_fields['is_superuser'].disabled = True


        return form


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    model = Entry
    list_display = [
        'get_contest_title',
        'get_style_name',
        'brewer',
        'name',
        'is_paid',
        'is_received',
        'extra_info',
    ]
    readonly_fields = [
        'modified_at',
    ]
    list_filter = [
        'is_paid',
        'is_received',
        'category__contest__title',
        'category__style__name',
    ]
    search_fields = [
        'brewer__username',
        'brewer__first_name',
        'brewer__last_name',
        'brewer__email',
    ]

    @admin.display(ordering='category__contest__title', description=_('Contest'))
    def get_contest_title(self, obj):
        return obj.category.contest.title



    @admin.display(ordering='category__style__name', description=_('Style'))
    def get_style_name(self, obj):
        return obj.category.style.name
