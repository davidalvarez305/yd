# Generated by Django 5.1.7 on 2025-05-28 02:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_unitconversion'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventshoppinglistentry',
            name='store',
            field=models.ForeignKey(db_column='store_id', default=1, on_delete=django.db.models.deletion.RESTRICT, to='core.store'),
            preserve_default=False,
        ),
    ]
