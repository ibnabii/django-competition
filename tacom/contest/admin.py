from django.contrib import admin
from django.db.models import TextField
from django.utils.translation import gettext_lazy as _
from tinymce.widgets import TinyMCE

from .models import Contest, Style, Entry, Category, User, Participant


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
    save_on_top = True
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
                'fields': ['title', 'slug', 'logo']
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
            _('Description in polish'),
            {
                'classes': ['collapse'],
                'fields': ['description_pl'],
            }
        ),
        (
            _('Delivery address'),
            {
                'classes': ['collapse'],
                'fields': ['delivery_address'],
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
            _('Fees'),
            {
                'fields': [
                    ('entry_fee_amount', 'entry_fee_currency')
                ]
            }
        ),
        (
            _('Limits'),
            {
                'fields': [
                    ('entry_global_limit', 'entry_user_limit')
                ]
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

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    readonly_fields = [
        'date_joined',
        'last_login',
    ]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        is_superuser = request.user.is_superuser

        if not is_superuser:
            form.base_fields['user_permissions'].disabled = True
            form.base_fields['is_staff'].disabled = True
            form.base_fields['is_superuser'].disabled = True
        return form


class EntriesForParticipant(admin.TabularInline):
    model = Entry
    extra = 0
    readonly_fields = (
        'id',
        'style',
        'name',
        'extra_info',
        'is_paid',
        'is_received'
    )
    exclude = ('category',)
    show_change_link = True

    def style(self, obj):
        return obj.category.style.name

    def has_add_permission(self, request, obj):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    f = (
        'username',
        'first_name',
        'last_name',
        'email',
        'phone',
        'address',
        'date_joined',
        'last_login'
    )
    fields = (
        'is_active',
        *f
    )
    readonly_fields = f

    inlines = (EntriesForParticipant,)
    save_on_top = True


    list_display = (
        'username',
        'last_name',
        'first_name',
        'email',
        'phone',
        'entries_total',
        'entries_paid',
        'entries_received'
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('entries')


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

    @admin.register(Category)
    class CategoryAdmin(admin.ModelAdmin):
        pass
