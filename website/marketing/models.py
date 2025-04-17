from django.db import models
import json
from .enums import ConversionServiceType
from core.models import Lead

AD_PLATFORMS = [
    (ConversionServiceType.GOOGLE.value, "Google"),
    (ConversionServiceType.FACEBOOK.value, "Facebook"),
]

class InstantForm(models.Model):
    instant_form_id = models.BigIntegerField()
    name = models.CharField(max_length=255, null=True)

class MarketingCampaign(models.Model):
    marketing_campaign_id = models.BigIntegerField()
    platform_id = models.IntegerField(choices=AD_PLATFORMS)

    class Meta:
        unique_together = ('marketing_campaign_id', 'platform_id')

class LeadMarketing(models.Model):
    lead_marketing_id = models.AutoField(primary_key=True)
    lead = models.OneToOneField(Lead, related_name='lead_marketing', db_column='lead_id', on_delete=models.CASCADE)
    source = models.CharField(max_length=255, null=True)
    medium = models.CharField(max_length=255, null=True)
    channel = models.CharField(max_length=255, null=True)
    landing_page = models.TextField(null=True)
    keyword = models.CharField(max_length=255, null=True)
    referrer = models.TextField(null=True)
    click_id = models.TextField(unique=True, null=True)
    client_id = models.TextField(unique=True, null=True)
    button_clicked = models.CharField(max_length=255, null=True)
    ip = models.GenericIPAddressField(null=True)
    external_id = models.CharField(max_length=255, db_index=True)
    instant_form_lead_id = models.BigIntegerField(null=True)
    instant_form = models.ForeignKey(InstantForm, null=True, related_name='lead_marketing', db_column='instant_form_id', on_delete=models.SET_NULL)
    marketing_campaign = models.ForeignKey(MarketingCampaign, null=True, related_name='lead_marketing', db_column='marketing_campaign_id', on_delete=models.SET_NULL)

    def __str__(self):
        return f"Marketing info for Lead {self.lead_id}"
    
    def is_instant_form_lead(self):
        return self.instant_form_lead_id is not None
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        Visit.objects.filter(external_id=self.external_id).update(lead_marketing=self)

    class Meta:
        db_table = 'lead_marketing'

class ConversionLog(models.Model):
    conversion_log_id = models.AutoField(primary_key=True)
    date_created = models.DateTimeField(auto_now_add=True)
    endpoint = models.URLField()
    payload = models.TextField()
    status_code = models.IntegerField()
    response = models.TextField(null=True)
    conversion_service_type_id = models.IntegerField(choices=AD_PLATFORMS)

    def __str__(self):
        return f"Conversion Log {self.conversion_log_id} - {self.date_created}"

    def save(self, *args, **kwargs):
        if isinstance(self.payload, dict):
            self.payload = json.dumps(self.payload)
        if isinstance(self.response, dict):
            self.response = json.dumps(self.response)
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'conversion_log'

class CallTrackingNumber(models.Model):
    call_tracking_number_id = models.AutoField(primary_key=True)
    call_tracking_number = models.CharField(max_length=15)
    marketing_campaign = models.ForeignKey(
        MarketingCampaign,
        related_name='call_tracking_numbers',
        on_delete=models.SET_NULL,
        db_column='marketing_campaign_id',
        null=True,
    )

    def __str__(self):
        return self.call_tracking_number

    class Meta:
        db_table = 'call_tracking_number'

class CallTracking(models.Model):
    call_tracking_id = models.AutoField(primary_key=True)
    call_tracking_number = models.ForeignKey(
        CallTrackingNumber,
        on_delete=models.CASCADE,
        db_column='call_tracking_number_id',
        related_name='call_trackings'
    )
    date_assigned = models.DateTimeField()
    date_expires = models.DateTimeField()
    client_id = models.CharField(max_length=255, db_index=True)
    click_id = models.CharField(max_length=255, db_index=True, unique=True)
    external_id = models.CharField(max_length=255, db_index=True)

    def __str__(self):
        return str(self.call_tracking_number)

    class Meta:
        db_table = 'call_tracking'

class LandingPage(models.Model):
    landing_page_id = models.AutoField(primary_key=True)
    url = models.SlugField()
    template = models.CharField(max_length=255)

    def __str__(self):
        return str(self.url)

    class Meta:
        db_table = 'landing_page'

class Visit(models.Model):
    visit_id = models.AutoField(primary_key=True)
    external_id = models.CharField(max_length=255, db_index=True)
    referrer = models.URLField(null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    url = models.URLField()
    session_duration = models.FloatField(default=0.0)
    
    lead_marketing = models.ForeignKey(LeadMarketing,
        null=True, on_delete=models.SET_NULL,
        related_name='visits'
    )

    def __str__(self):
        return f"Visit {self.visit_id} - {self.url} from {self.referrer}"

    class Meta:
        db_table = 'visit'