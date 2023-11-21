from django import template

register = template.Library()


@register.filter(name='is_translator')
def is_translator(user):
    return user.groups.filter(name='translators').exists()


@register.filter(name='is_contest_staff')
def is_contest_staff(user):
    return user.groups.filter(name='contest_staff').exists()


@register.filter(name='is_reception')
def is_contest_staff(user):
    return user.groups.filter(name='reception').exists()
