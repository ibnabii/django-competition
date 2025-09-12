from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ContestConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'contest'
    # Translators: name of the app that's displayed in admin panel for managing data
    verbose_name = _('Competitions')
