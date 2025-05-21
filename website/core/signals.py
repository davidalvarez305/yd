from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Lead, LeadMarketing, MarketingCampaign, PhoneCall
from core.models import CallTracking

@receiver(post_save, sender=Lead)
def handle_lead_save(sender, instance: Lead, created, **kwargs) -> None:
    """
    This function is called when a lead record is saved.
    It checks if the call_from (lead phone number) and call_to (call tracking number) match in the phone call table.
    If there's a match, it assigns campaign-level data associated with that call tracking number to the marketing table & reports conversion to appropriate ad platform.
    """
    if created:
        try:
            lead_marketing = LeadMarketing.objects.filter(lead=instance).first()

            if not lead_marketing:
                raise ValueError('Lead marketing not found.')

            if lead_marketing.is_instant_form_lead():
                return

            first_inbound_call = PhoneCall.objects.filter(call_from=instance.phone_number).order_by('date_created').first()

            tracking_call = (
                CallTracking.objects
                .filter(
                    phone_number=first_inbound_call.call_to,
                    date_assigned__lt=first_inbound_call.date_created,
                    date_expires__gt=first_inbound_call.date_created,
                )
                .order_by('-date_created')
                .first()
            )

            if not tracking_call:
                return
            
            for key, value in tracking_call.metadata.items():
                if hasattr(lead_marketing, key):
                    setattr(lead_marketing, key, value)

            campaign_id = getattr(tracking_call.metadata, 'marketing_campaign_id', None)
            campaign_name = getattr(tracking_call.metadata, 'marketing_campaign_name', None)

            lead_marketing.marketing_campaign = MarketingCampaign.objects.get_or_create(
                marketing_campaign_id=campaign_id,
                platform_id=lead_marketing.platform_id,
                name=campaign_name,
            )

            lead_marketing.save()

        except Exception as e:
            print(f"Error processing lead save: {str(e)}")