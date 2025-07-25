# Generated by Django 5.1.7 on 2025-07-11 03:11

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0052_alter_leadmarketing_user_agent'),
    ]

    operations = [
        migrations.CreateModel(
            name='PhoneCallStatusHistory',
            fields=[
                ('phone_call_status_history_id', models.AutoField(primary_key=True, serialize=False)),
                ('status', models.CharField(max_length=50)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('phone_call', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.phonecall')),
            ],
            options={
                'db_table': 'phone_call_status_history',
            },
        ),
    ]
