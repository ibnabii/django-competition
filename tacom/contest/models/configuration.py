from uuid import uuid4
from django.db import models


class ConfigurationOption(models.TextChoices):
    SEND_EMAILS = "send_emails", "Send emails"


class Configuration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    key = models.CharField(
        max_length=100, unique=True, choices=ConfigurationOption.choices
    )
    value = models.CharField(max_length=100)
