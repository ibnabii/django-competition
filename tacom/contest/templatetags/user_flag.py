from django import template

register = template.Library()


@register.simple_tag
def flag(user):
    if user.language == 'en':
        lang = 'gb'
    else:
        lang = user.language

    return f'flags/{lang}.gif'
