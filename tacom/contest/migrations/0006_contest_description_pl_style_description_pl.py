# Generated by Django 4.2 on 2023-11-14 07:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contest', '0005_user_country_user_language'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='description_pl',
            field=models.TextField(null=True, verbose_name='Description in polish'),
        ),
        migrations.AddField(
            model_name='style',
            name='description_pl',
            field=models.TextField(null=True, verbose_name='Description in polish'),
        ),
    ]
