# Generated by Django 5.1.7 on 2025-04-15 23:06

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='date_created',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='event',
            name='date_paid',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
