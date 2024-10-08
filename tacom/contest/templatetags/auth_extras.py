from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def get_user_permissions(context):
    user = context["request"].user
    groups = user.groups.values_list("name", flat=True)
    return {
        "is_translator": "translators" in groups,
        "is_contest_staff": "contest_staff" in groups,
        "is_reception": "reception" in groups,
        "is_payment_mgmt": "payment_mgmt" in groups,
        "is_judge": "judge" in groups,
        "is_judge_final": "judge_final" in groups,
    }
