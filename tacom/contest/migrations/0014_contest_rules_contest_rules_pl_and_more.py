# Generated by Django 4.2 on 2024-09-11 13:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contest', '0013_entry_alcohol_content_entry_carbonation_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='rules',
            field=models.TextField(blank=True, verbose_name='Rules'),
        ),
        migrations.AddField(
            model_name='contest',
            name='rules_pl',
            field=models.TextField(blank=True, verbose_name='Rules in polish'),
        ),
        migrations.AlterField(
            model_name='entry',
            name='carbonation',
            field=models.CharField(choices=[('still', 'Still'), ('petillant', 'Petillant'), ('sparkling', 'Sparkling')], max_length=10, verbose_name='Carbonation'),
        ),
        migrations.AlterField(
            model_name='entry',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to='contest.category', verbose_name='Category'),
        ),
        migrations.AlterField(
            model_name='entry',
            name='sweetness',
            field=models.CharField(choices=[('dry', 'Dry'), ('medium', 'Medium'), ('sweet', 'Sweet')], max_length=10, verbose_name='Sweetness'),
        ),
    ]
