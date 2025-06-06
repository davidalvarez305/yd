# Generated by Django 5.1.7 on 2025-05-21 00:41

import core.models
import django.contrib.postgres.search
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='CallTrackingNumber',
            fields=[
                ('call_tracking_number_id', models.AutoField(primary_key=True, serialize=False)),
                ('call_tracking_number', models.CharField(max_length=15)),
            ],
            options={
                'db_table': 'call_tracking_number',
            },
        ),
        migrations.CreateModel(
            name='Cocktail',
            fields=[
                ('cocktail_id', models.IntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'db_table': 'cocktail',
            },
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('event_id', models.IntegerField(primary_key=True, serialize=False)),
                ('street_address', models.CharField(max_length=255, null=True)),
                ('city', models.CharField(max_length=100, null=True)),
                ('zip_code', models.CharField(max_length=20, null=True)),
                ('start_time', models.DateTimeField(null=True)),
                ('end_time', models.DateTimeField(null=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_paid', models.DateTimeField(default=django.utils.timezone.now)),
                ('amount', models.FloatField()),
                ('tip', models.FloatField(null=True)),
                ('guests', models.IntegerField()),
            ],
            options={
                'db_table': 'event',
            },
        ),
        migrations.CreateModel(
            name='EventRole',
            fields=[
                ('event_role_id', models.IntegerField(primary_key=True, serialize=False)),
                ('role', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'event_role',
            },
        ),
        migrations.CreateModel(
            name='HTTPLog',
            fields=[
                ('http_log_id', models.AutoField(primary_key=True, serialize=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now)),
                ('method', models.CharField(max_length=10)),
                ('url', models.URLField()),
                ('query_params', models.JSONField(null=True)),
                ('payload', models.JSONField(null=True)),
                ('headers', models.JSONField(null=True)),
                ('response', models.JSONField(null=True)),
                ('status_code', models.IntegerField(null=True)),
                ('error', models.JSONField(null=True)),
                ('duration_seconds', models.FloatField(null=True)),
                ('retries', models.IntegerField(default=0)),
                ('service_name', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'http_log',
                'ordering': ['-date_created'],
            },
        ),
        migrations.CreateModel(
            name='InstantForm',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('instant_form_id', models.BigIntegerField()),
                ('name', models.CharField(max_length=255, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='InvoiceType',
            fields=[
                ('invoice_type_id', models.IntegerField(primary_key=True, serialize=False)),
                ('type', models.CharField(max_length=100)),
                ('amount_percentage', models.FloatField()),
            ],
            options={
                'db_table': 'invoice_type',
            },
        ),
        migrations.CreateModel(
            name='LandingPage',
            fields=[
                ('landing_page_id', models.AutoField(primary_key=True, serialize=False)),
                ('url', models.SlugField()),
                ('template', models.CharField(max_length=255)),
            ],
            options={
                'db_table': 'landing_page',
            },
        ),
        migrations.CreateModel(
            name='Lead',
            fields=[
                ('lead_id', models.AutoField(primary_key=True, serialize=False)),
                ('full_name', models.CharField(max_length=100)),
                ('phone_number', models.CharField(max_length=15, unique=True)),
                ('opt_in_text_messaging', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('email', models.EmailField(max_length=254, null=True, unique=True)),
                ('message', models.TextField(null=True)),
                ('stripe_customer_id', models.CharField(max_length=255, null=True, unique=True)),
                ('search_vector', django.contrib.postgres.search.SearchVectorField(null=True)),
            ],
            options={
                'db_table': 'lead',
            },
        ),
        migrations.CreateModel(
            name='LeadInterest',
            fields=[
                ('lead_interest_id', models.IntegerField(primary_key=True, serialize=False)),
                ('interest', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='LeadStatus',
            fields=[
                ('lead_status_id', models.IntegerField(primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('LEAD_CREATED', 'Lead Created'), ('QUALIFIED_LEAD', 'Qualified Lead'), ('INVOICE_SENT', 'Invoice Sent'), ('EVENT_BOOKED', 'Event Booked')], max_length=50)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('message_id', models.AutoField(primary_key=True, serialize=False)),
                ('external_id', models.CharField(max_length=255, unique=True)),
                ('text', models.TextField()),
                ('date_created', models.DateTimeField(auto_now_add=True)),
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
            name='NextAction',
            fields=[
                ('next_action_id', models.IntegerField(primary_key=True, serialize=False)),
                ('action', models.CharField(max_length=255)),
            ],
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
            name='Service',
            fields=[
                ('service_id', models.IntegerField(primary_key=True, serialize=False)),
                ('service', models.CharField(max_length=255)),
                ('suggested_price', models.FloatField(null=True)),
                ('guest_ratio', models.IntegerField(null=True)),
            ],
            options={
                'db_table': 'service',
            },
        ),
        migrations.CreateModel(
            name='ServiceType',
            fields=[
                ('service_type_id', models.IntegerField(primary_key=True, serialize=False)),
                ('type', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'service_type',
            },
        ),
        migrations.CreateModel(
            name='UnitType',
            fields=[
                ('unit_type_id', models.IntegerField(primary_key=True, serialize=False)),
                ('type', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'unit_type',
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('user_id', models.AutoField(primary_key=True, serialize=False)),
                ('username', models.CharField(max_length=150, unique=True)),
                ('phone_number', models.CharField(max_length=20, unique=True)),
                ('forward_phone_number', models.CharField(max_length=20, unique=True)),
                ('first_name', models.CharField(max_length=50)),
                ('last_name', models.CharField(max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=False)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'db_table': 'user',
            },
        ),
        migrations.CreateModel(
            name='CallTracking',
            fields=[
                ('call_tracking_id', models.AutoField(primary_key=True, serialize=False)),
                ('date_assigned', models.DateTimeField()),
                ('date_expires', models.DateTimeField()),
                ('metadata', models.JSONField(null=True)),
                ('external_id', models.CharField(max_length=255)),
                ('call_tracking_number', models.ForeignKey(db_column='call_tracking_number_id', on_delete=django.db.models.deletion.CASCADE, related_name='calls', to='core.calltrackingnumber')),
            ],
            options={
                'db_table': 'call_tracking',
            },
        ),
        migrations.CreateModel(
            name='EventCocktail',
            fields=[
                ('event_cocktail_id', models.IntegerField(primary_key=True, serialize=False)),
                ('cocktail', models.ForeignKey(db_column='cocktail_id', on_delete=django.db.models.deletion.CASCADE, to='core.cocktail')),
                ('event', models.ForeignKey(db_column='event_id', on_delete=django.db.models.deletion.CASCADE, to='core.event')),
            ],
            options={
                'db_table': 'event_cocktail',
                'unique_together': {('cocktail', 'event')},
            },
        ),
        migrations.AddField(
            model_name='event',
            name='cocktails',
            field=models.ManyToManyField(related_name='events', through='core.EventCocktail', to='core.cocktail'),
        ),
        migrations.CreateModel(
            name='EventStaff',
            fields=[
                ('event_staff_id', models.IntegerField(primary_key=True, serialize=False)),
                ('hourly_rate', models.FloatField()),
                ('event', models.ForeignKey(db_column='event_id', on_delete=django.db.models.deletion.CASCADE, to='core.event')),
                ('event_role', models.ForeignKey(db_column='event_role_id', on_delete=django.db.models.deletion.RESTRICT, to='core.eventrole')),
                ('user', models.ForeignKey(db_column='user_id', on_delete=django.db.models.deletion.RESTRICT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'event_staff',
            },
        ),
        migrations.AddField(
            model_name='user',
            name='events',
            field=models.ManyToManyField(related_name='staff', through='core.EventStaff', to='core.event'),
        ),
        migrations.AddField(
            model_name='event',
            name='lead',
            field=models.ForeignKey(db_column='lead_id', on_delete=django.db.models.deletion.CASCADE, related_name='events', to='core.lead'),
        ),
        migrations.AddField(
            model_name='lead',
            name='lead_interest',
            field=models.ForeignKey(db_column='lead_interest_id', null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.leadinterest'),
        ),
        migrations.CreateModel(
            name='LeadNote',
            fields=[
                ('lead_note_id', models.IntegerField(primary_key=True, serialize=False)),
                ('note', models.TextField()),
                ('date_added', models.DateTimeField(auto_now_add=True)),
                ('lead', models.ForeignKey(db_column='lead_id', on_delete=django.db.models.deletion.CASCADE, related_name='notes', to='core.lead')),
                ('user', models.ForeignKey(db_column='added_by_user_id', on_delete=django.db.models.deletion.CASCADE, related_name='notes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'lead_note',
            },
        ),
        migrations.AddField(
            model_name='lead',
            name='lead_status',
            field=models.ForeignKey(db_column='lead_status_id', null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.leadstatus'),
        ),
        migrations.CreateModel(
            name='LeadStatusHistory',
            fields=[
                ('lead_status_history_id', models.AutoField(primary_key=True, serialize=False)),
                ('date_changed', models.DateTimeField(auto_now_add=True)),
                ('lead', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.lead')),
                ('lead_status', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.leadstatus')),
            ],
        ),
        migrations.CreateModel(
            name='MarketingCampaign',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('marketing_campaign_id', models.BigIntegerField()),
                ('name', models.TextField()),
                ('platform_id', models.IntegerField(choices=[(1, 'Google'), (2, 'Facebook')])),
            ],
            options={
                'unique_together': {('marketing_campaign_id', 'platform_id')},
            },
        ),
        migrations.CreateModel(
            name='LeadMarketing',
            fields=[
                ('lead_marketing_id', models.AutoField(primary_key=True, serialize=False)),
                ('source', models.CharField(max_length=255, null=True)),
                ('medium', models.CharField(max_length=255, null=True)),
                ('channel', models.CharField(max_length=255, null=True)),
                ('landing_page', models.TextField(null=True)),
                ('keyword', models.CharField(max_length=255, null=True)),
                ('referrer', models.TextField(null=True)),
                ('click_id', models.TextField(null=True, unique=True)),
                ('client_id', models.TextField(null=True, unique=True)),
                ('button_clicked', models.CharField(max_length=255, null=True)),
                ('ip', models.GenericIPAddressField(null=True)),
                ('external_id', models.CharField(db_index=True, max_length=255)),
                ('instant_form_lead_id', models.BigIntegerField(null=True)),
                ('instant_form', models.ForeignKey(db_column='instant_form_id', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lead_marketing', to='core.instantform')),
                ('lead', models.OneToOneField(db_column='lead_id', on_delete=django.db.models.deletion.CASCADE, related_name='lead_marketing', to='core.lead')),
                ('marketing_campaign', models.ForeignKey(db_column='marketing_campaign_id', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lead_marketing', to='core.marketingcampaign')),
            ],
            options={
                'db_table': 'lead_marketing',
            },
        ),
        migrations.CreateModel(
            name='MessageMedia',
            fields=[
                ('message_media_id', models.AutoField(primary_key=True, serialize=False)),
                ('content_type', models.CharField(max_length=100)),
                ('file', models.FileField(upload_to=core.models.media_upload_path)),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media', to='core.message')),
            ],
            options={
                'db_table': 'message_media',
            },
        ),
        migrations.CreateModel(
            name='LeadNextAction',
            fields=[
                ('lead_next_action_id', models.IntegerField(primary_key=True, serialize=False)),
                ('action_date', models.DateTimeField()),
                ('lead', models.ForeignKey(db_column='lead_id', on_delete=django.db.models.deletion.CASCADE, to='core.lead')),
                ('next_action', models.ForeignKey(db_column='next_action_id', on_delete=django.db.models.deletion.CASCADE, to='core.nextaction')),
            ],
        ),
        migrations.AddField(
            model_name='lead',
            name='actions',
            field=models.ManyToManyField(through='core.LeadNextAction', to='core.nextaction'),
        ),
        migrations.CreateModel(
            name='PhoneCallTranscription',
            fields=[
                ('phone_call_transcription_id', models.AutoField(primary_key=True, serialize=False)),
                ('external_id', models.CharField(max_length=255, unique=True)),
                ('text', models.TextField()),
                ('audio', models.FileField(upload_to='audio/')),
                ('job', models.JSONField(null=True)),
                ('phone_call', models.ForeignKey(db_column='phone_call_id', on_delete=django.db.models.deletion.CASCADE, related_name='transcriptions', to='core.phonecall')),
            ],
            options={
                'db_table': 'phone_call_transcription',
            },
        ),
        migrations.CreateModel(
            name='Quote',
            fields=[
                ('quote_id', models.IntegerField(primary_key=True, serialize=False)),
                ('external_id', models.CharField(max_length=100)),
                ('guests', models.IntegerField()),
                ('hours', models.FloatField()),
                ('event_date', models.DateTimeField()),
                ('lead', models.ForeignKey(db_column='lead_id', on_delete=django.db.models.deletion.CASCADE, related_name='quotes', to='core.lead')),
            ],
            options={
                'db_table': 'quote',
            },
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('invoice_id', models.IntegerField(primary_key=True, serialize=False)),
                ('date_created', models.DateTimeField()),
                ('date_paid', models.DateTimeField()),
                ('due_date', models.DateTimeField()),
                ('url', models.TextField(max_length=255)),
                ('stripe_invoice_id', models.CharField(max_length=100, unique=True)),
                ('invoice_type', models.ForeignKey(db_column='invoice_type_id', on_delete=django.db.models.deletion.RESTRICT, to='core.invoicetype')),
                ('quote', models.ForeignKey(db_column='quote_id', on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='core.quote')),
            ],
            options={
                'db_table': 'invoice',
            },
        ),
        migrations.CreateModel(
            name='QuoteService',
            fields=[
                ('quote_service_id', models.IntegerField(primary_key=True, serialize=False)),
                ('units', models.FloatField()),
                ('price_per_unit', models.FloatField()),
                ('quote', models.ForeignKey(db_column='quote_id', on_delete=django.db.models.deletion.RESTRICT, related_name='quote_services', to='core.quote')),
                ('service', models.ForeignKey(db_column='service_id', on_delete=django.db.models.deletion.RESTRICT, to='core.service')),
            ],
            options={
                'db_table': 'quote_service',
            },
        ),
        migrations.AddField(
            model_name='quote',
            name='services',
            field=models.ManyToManyField(related_name='quote_services', through='core.QuoteService', to='core.service'),
        ),
        migrations.AddField(
            model_name='service',
            name='service_type',
            field=models.ForeignKey(db_column='service_type_id', on_delete=django.db.models.deletion.RESTRICT, to='core.servicetype'),
        ),
        migrations.AddField(
            model_name='service',
            name='unit_type',
            field=models.ForeignKey(db_column='unit_type_id', on_delete=django.db.models.deletion.RESTRICT, to='core.unittype'),
        ),
        migrations.CreateModel(
            name='Visit',
            fields=[
                ('visit_id', models.AutoField(primary_key=True, serialize=False)),
                ('external_id', models.CharField(db_index=True, max_length=255)),
                ('referrer', models.URLField(null=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('url', models.URLField()),
                ('session_duration', models.FloatField(default=0.0)),
                ('lead_marketing', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='visits', to='core.leadmarketing')),
            ],
            options={
                'db_table': 'visit',
                'ordering': ['-date_created'],
            },
        ),
    ]
