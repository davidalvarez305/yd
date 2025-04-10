
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Lead
from website.communication.models import PhoneCall
from website.marketing.models import CallTracking
from website.marketing.conversions import report_conversion, ConversionPayload, ConversionEventType

@receiver(post_save, sender=Lead)
def handle_lead_save(sender, instance, created, **kwargs) -> None:
    """
    This function is called when a lead record is saved.
    It checks if the call_from (lead phone number) and call_to (call tracking number) match in the phone call table.
    If there's a match, it assigns campaign-level data associated with that call tracking number to the marketing table & reports conv to appropriate ad platform.
    """
    if created:
        try:
            # Step 1: Get the lead's phone number and the tracking phone number
            lead_phone_number = instance.phone_number

            if not lead_phone_number:
                return

            # Step 2: Query the phone call table for any phone calls made by this number
            phone_call = PhoneCall.objects.filter(call_from=lead_phone_number).first()

            # Step 3: Check if phone call came BEFORE lead was created -- indicating that the person called before a quote submission
            if not phone_call or phone_call.date_created > instance.created_at:
                return

            # Step 4: Identify instance
            tracking_call = CallTracking.objects.filter(phone_number=phone_call.call_to).first()

            if not tracking_call:
                return

            call_tracking_date_expires = tracking_call.date_expires

            if phone_call.date_created > call_tracking_date_expires:
                return

            # Step 5: Trigger the workflow to assign google or facebook campaign attribution 
            trigger_workflow(phone_call_match)

            # Step 6: Report lead to google or facebook, where applicable
            conversion_payload = ConversionPayload(
                conversion_event_type=ConversionEventType.WebsiteCall,
                platform_id=instance.marketing.platform_id,
                campaign_id=instance.marketing.campaign.campaign_id,
                click_id=instance.marketing.click_id,
                client_id=instance.marketing.client_id,
                external_id=instance.marketing.external_id,
                phone_number=instance.phone_number,
                email=instance.email,
                full_name=instance.full_name
            )

            report_conversion(conversion_payload=conversion_payload)
        except CallTracking.DoesNotExist as e:
            logger.error(f"Error processing CallTracking save: {str(e)}")