# Generated by Django 5.1.7 on 2025-04-15 23:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('message_id', models.AutoField(primary_key=True, serialize=False)),
                ('external_id', models.CharField(max_length=255, unique=True)),
                ('text', models.TextField()),
                ('date_created', models.DateTimeField()),
                ('text_from', models.CharField(max_length=10)),
                ('text_to', models.CharField(max_length=10)),
                ('is_inbound', models.BooleanField(default=False)),
                ('status', models.CharField(max_length=50)),
                ('is_read', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'message',
            },
        ),
        migrations.CreateModel(
            name='PhoneCall',
            fields=[
                ('phone_call_id', models.AutoField(primary_key=True, serialize=False)),
                ('external_id', models.CharField(max_length=255, unique=True)),
                ('call_duration', models.IntegerField()),
                ('date_created', models.DateTimeField()),
                ('call_from', models.CharField(max_length=10)),
                ('call_to', models.CharField(max_length=10)),
                ('is_inbound', models.BooleanField(default=False)),
                ('recording_url', models.TextField(null=True)),
                ('status', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'phone_call',
            },
        ),
        migrations.CreateModel(
            name='PhoneCallTranscription',
            fields=[
                ('phone_call_transcription_id', models.AutoField(primary_key=True, serialize=False)),
                ('external_id', models.CharField(max_length=255, unique=True)),
                ('text', models.TextField()),
                ('audio_url', models.TextField()),
                ('text_url', models.TextField()),
                ('phone_call', models.ForeignKey(db_column='phone_call_id', on_delete=django.db.models.deletion.CASCADE, related_name='transcriptions', to='communication.phonecall')),
            ],
            options={
                'db_table': 'phone_call_transcription',
            },
        ),
    ]
