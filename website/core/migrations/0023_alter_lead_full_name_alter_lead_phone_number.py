# Generated by Django 5.1.7 on 2025-05-31 18:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_remove_calltrackingnumber_call_tracking_number_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lead',
            name='full_name',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='lead',
            name='phone_number',
            field=models.CharField(max_length=60, unique=True),
        ),
    ]
