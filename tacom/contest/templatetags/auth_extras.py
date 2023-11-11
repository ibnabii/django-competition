from django import template

register = template.Library()


@register.filter(name='is_translator')
def is_translator(user):
    return user.groups.filter(name='translators').exists()
