# Generated by Django 4.2 on 2023-11-17 19:41

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('contest', '0008_entriespackage'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentMethod',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid1, editable=False, primary_key=True, serialize=False)),
                ('logo', models.ImageField(blank=True, help_text='Displayed at payment method selection page', null=True, upload_to='')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
                ('name_pl', models.CharField(max_length=50, verbose_name='Polish name')),
                ('code', models.CharField(help_text='Code is used by the software, do not change!', max_length=10, unique=True, verbose_name='Method code')),
            ],
        ),
        migrations.AddField(
            model_name='contest',
            name='payment_transfer_info',
            field=models.TextField(blank=True, help_text='Mandatory if contest allows transfer payment method.', verbose_name='Transfer payment instructions'),
        ),
        migrations.AlterField(
            model_name='entriespackage',
            name='entries',
            field=models.ManyToManyField(related_name='packages', to='contest.entry'),
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid1, editable=False, primary_key=True, serialize=False)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Amount')),
                ('currency', models.CharField(max_length=3, verbose_name='Currency')),
                ('status', models.CharField(choices=[('created', 'Created'), ('canceled', 'Canceled'), ('ok', 'OK'), ('failed', 'Failed'), ('awaiting', 'Confirmation pending')], default='created', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('contest', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='contest.contest', verbose_name='Contest')),
                ('entries', models.ManyToManyField(related_name='payments', to='contest.entry', verbose_name='Entries')),
                ('method', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='contest.paymentmethod', verbose_name='Method')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'payment',
                'verbose_name_plural': 'payments',
                'ordering': ('-created_at',),
            },
        ),
        migrations.AddField(
            model_name='contest',
            name='payment_methods',
            field=models.ManyToManyField(related_name='contests', to='contest.paymentmethod', verbose_name='Allowed payment methods'),
        ),
    ]
