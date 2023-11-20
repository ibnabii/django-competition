# Generated by Django 4.2 on 2023-11-15 22:09

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('contest', '0007_entry_code'),
    ]

    operations = [
        migrations.CreateModel(
            name='EntriesPackage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid1, editable=False, primary_key=True, serialize=False)),
                ('contest', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='contest.contest')),
                ('entries', models.ManyToManyField(to='contest.entry')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='packages', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]