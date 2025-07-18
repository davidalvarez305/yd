# Generated by Django 5.1.7 on 2025-06-13 23:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0032_invoice_amount_alter_invoice_date_created_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='FacebookAccessToken',
            fields=[
                ('facebook_access_token_id', models.AutoField(primary_key=True, serialize=False)),
                ('access_token', models.TextField()),
                ('date_expires', models.DateTimeField()),
                ('date_created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'facebook_access_token',
            },
        ),
        migrations.RenameField(
            model_name='invoice',
            old_name='url',
            new_name='session_id',
        ),
    ]
