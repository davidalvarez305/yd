from django.db import models

class Lead(models.Model):
    lead_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    opt_in_text_messaging = models.BooleanField(default=True)
    created_at = models.DateTimeField()

    # Nullable fields
    email = models.EmailField(null=True)
    message = models.TextField(null=True)

    # Workflow fields
    lead_interest_id = models.IntegerField()
    lead_status_id = models.IntegerField()

    def __str__(self):
        return self.full_name

    class Meta:
        db_table = 'lead'


class LeadMarketing(models.Model):
    lead_marketing_id = models.AutoField(primary_key=True)
    lead = models.ForeignKey(Lead, related_name='marketing', on_delete=models.CASCADE)
    source = models.CharField(max_length=255)
    medium = models.CharField(max_length=255)
    channel = models.CharField(max_length=255)
    landing_page = models.URLField(null=True, blank=True)
    longitude = models.CharField(max_length=50, null=True, blank=True)
    latitude = models.CharField(max_length=50, null=True, blank=True)
    keyword = models.CharField(max_length=255, null=True, blank=True)
    referrer = models.URLField(null=True, blank=True)
    click_id = models.CharField(max_length=255, null=True, blank=True)
    campaign_id = models.BigIntegerField()
    ad_campaign = models.CharField(max_length=255, null=True, blank=True)
    ad_group_id = models.BigIntegerField()
    ad_group_name = models.CharField(max_length=255, null=True, blank=True)
    ad_set_id = models.BigIntegerField()
    ad_set_name = models.CharField(max_length=255, null=True, blank=True)
    ad_id = models.BigIntegerField()
    ad_headline = models.BigIntegerField()
    language = models.CharField(max_length=50, null=True, blank=True)
    os = models.CharField(max_length=50, null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    button_clicked = models.CharField(max_length=255, null=True, blank=True)
    device_type = models.CharField(max_length=50, null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    google_client_id = models.CharField(max_length=255, null=True, blank=True)
    facebook_click_id = models.CharField(max_length=255, null=True, blank=True)
    facebook_client_id = models.CharField(max_length=255, null=True, blank=True)
    csrf_secret = models.CharField(max_length=255, null=True, blank=True)
    instant_form_lead_id = models.BigIntegerField(null=True, blank=True)
    instant_form_id = models.BigIntegerField(null=True, blank=True)
    instant_form_name = models.CharField(max_length=255, null=True, blank=True)
    referral_lead_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Marketing info for Lead {self.lead_id}"

    class Meta:
        db_table = 'lead_marketing'
