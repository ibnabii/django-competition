# Generated by Django 4.2 on 2023-04-13 18:28

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contest', '0006_contest_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contest',
            name='created_by',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='created_contests', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='contest',
            name='modified_by',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='modified_contests', to=settings.AUTH_USER_MODEL),
        ),
    ]
