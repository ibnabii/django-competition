import copy

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import TextField
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin
from tinymce.widgets import TinyMCE

from .models import (
    Category,
    Contest,
    EntriesPackage,
    Entry,
    Participant,
    Payment,
    PaymentMethod,
    RebateCode,
    ScoreSheet,
    Style,
    User,
)


@admin.register(Style)
class StyleAdmin(admin.ModelAdmin):
    model = Style
    formfield_overrides = {
        TextField: {"widget": TinyMCE(attrs={"cols": 80, "rows": 30})},
    }
    readonly_fields = ["created_at", "created_by", "modified_at", "modified_by"]

    def save_model(self, request, obj, form, change):
        obj.modified_by = request.user
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class CategoriesForContest(admin.TabularInline):
    model = Contest.styles.through
    extra = 0


@admin.action(description=_("Create copies of selected objects"))
def duplicate_contest(_modeladmin, _request, queryset):
    for obj in queryset:
        obj_copy = copy.copy(obj)
        obj_copy.pk = None  # This will save as a new object
        obj_copy.slug = ""
        obj_copy.title = f"{obj.title} ({_('copy')})"
        obj_copy.save()
        # If your model has many-to-many fields, also duplicate them
        for m2m_field in obj._meta.many_to_many:
            field = getattr(obj, m2m_field.name)
            getattr(obj_copy, m2m_field.name).set(field.all())


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    actions = [duplicate_contest]
    # save_on_top = True
    model = Contest
    inlines = (CategoriesForContest,)
    save_on_top = True
    # filter_horizontal = ('categories', )
    readonly_fields = ["created_at", "created_by", "modified_at", "modified_by"]
    formfield_overrides = {
        TextField: {"widget": TinyMCE(attrs={"cols": 80, "rows": 30})},
    }
    fieldsets = [
        (None, {"fields": ["title", "slug", "logo"]}),
        (
            _("Description"),
            {
                "classes": ["collapse"],
                "fields": ["description"],
            },
        ),
        (
            _("Description in polish"),
            {
                "classes": ["collapse"],
                "fields": ["description_pl"],
            },
        ),
        (
            _("Rules"),
            {
                "classes": ["collapse"],
                "fields": ["rules"],
            },
        ),
        (
            _("Rules in polish"),
            {
                "classes": ["collapse"],
                "fields": ["rules_pl"],
            },
        ),
        (
            _("Delivery address"),
            {
                "classes": ["collapse"],
                "fields": ["delivery_address"],
            },
        ),
        (
            _("Fees"),
            {
                "classes": ["collapse"],
                "fields": [
                    ("entry_fee_amount", "entry_fee_currency"),
                    ("discount_rate",),
                    ("payment_methods",),
                    ("payment_transfer_info",),
                ],
            },
        ),
        (
            _("Judging"),
            {
                "fields": [
                    ("is_judging_eliminations",),
                    ("is_judging_finals",),
                    ("is_judging_bos",),
                ],
                "description": _(
                    "Check which part of judging you want to make available to judges NOW"
                ),
            },
        ),
        (_("Limits"), {"fields": [("entry_global_limit", "entry_user_limit")]}),
        (
            _("Dates"),
            {
                "fields": [
                    ("registration_date_from", "registration_date_to"),
                    ("delivery_date_from", "delivery_date_to"),
                    ("judging_date_from", "judging_date_to"),
                ]
            },
        ),
        (
            _("Publish competition page"),
            {
                "fields": [
                    "competition_is_published",
                    "competition_autopublish_datetime",
                ]
            },
        ),
        (
            _("Publish competition results"),
            {"fields": ["result_is_published", "result_autopublish_datetime"]},
        ),
        (
            _("Audit"),
            {"fields": [("created_at", "created_by"), ("modified_at", "modified_by")]},
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
class CustomUserAdmin(UserAdmin):
    readonly_fields = [
        "date_joined",
        "last_login",
    ]
    list_display = ("username", "last_name", "first_name", "email")
    list_display_links = list_display

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        is_superuser = request.user.is_superuser

        if not is_superuser:
            form.base_fields["user_permissions"].disabled = True
            form.base_fields["is_staff"].disabled = True
            form.base_fields["is_superuser"].disabled = True
        return form


class EntriesForParticipant(admin.TabularInline):
    model = Entry
    extra = 0
    readonly_fields = ("id", "style", "name", "extra_info", "is_paid", "is_received")
    exclude = ("category",)
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
        "username",
        "first_name",
        "last_name",
        "email",
        "phone",
        "address",
        "language",
        "date_joined",
        "last_login",
    )
    fields = ("is_active", *f)
    readonly_fields = f

    inlines = (EntriesForParticipant,)
    save_on_top = True

    list_display = (
        "username",
        "last_name",
        "first_name",
        "email",
        "phone",
        "entries_total",
        "entries_paid",
        "entries_received",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("entries")


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    model = Entry
    list_display = [
        # 'get_contest_title',
        "code",
        "brewer",
        "get_style_name",
        "name",
        "is_paid",
        "is_received",
        "extra_info",
    ]
    readonly_fields = [
        "modified_at",
    ]
    list_filter = [
        "is_paid",
        "is_received",
        "category__contest__title",
        "category__style__name",
    ]
    search_fields = [
        "brewer__username",
        "brewer__first_name",
        "brewer__last_name",
        "brewer__email",
    ]

    @admin.display(ordering="category__contest__title", description=_("Contest"))
    def get_contest_title(self, obj):
        return obj.category.contest.title

    @admin.display(ordering="category__style__name", description=_("Style"))
    def get_style_name(self, obj):
        return obj.category.style.name

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        # Set a flag to bypass validation if this is an admin form
        if obj is not None:
            obj._admin_skip_validation = True
        return form


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    pass


@admin.register(EntriesPackage)
class EntriesPackageAdmin(admin.ModelAdmin):
    pass


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    pass


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "created_at",
        "method",
        "status",
        "amount",
        "currency",
    )


@admin.register(ScoreSheet)
class ScoreSheetAdmin(SimpleHistoryAdmin):
    formfield_overrides = {
        TextField: {"widget": TinyMCE(attrs={"cols": 80, "rows": 100})},
    }


@admin.register(RebateCode)
class RebateCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "is_used", "user")

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        # Exclude is_used and user fields only when creating a new instance
        if not obj:
            return [field for field in fields if field not in ("is_used", "user")]
        return fields

    # Automatically set default values for is_used and user only when creating a new rebate code
    def save_model(self, request, obj, form, change):
        if not change:  # If the object is being created
            obj.is_used = False
            obj.user = None
        super().save_model(request, obj, form, change)
