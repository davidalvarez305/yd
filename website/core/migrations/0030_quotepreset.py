# Generated by Django 5.1.7 on 2025-06-08 05:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_remove_invoice_stripe_invoice_id_invoice_external_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuotePreset',
            fields=[
                ('quote_preset_id', models.AutoField(primary_key=True, serialize=False)),
                ('preset', models.JSONField()),
                ('name', models.CharField(max_length=255)),
                ('text_content', models.TextField()),
            ],
            options={
                'db_table': 'quote_preset',
            },
        ),
    ]
