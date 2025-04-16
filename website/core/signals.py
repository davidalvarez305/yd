
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Lead
from communication.models import PhoneCall
from marketing.models import CallTracking, LeadMarketing
from marketing.conversions import report_conversion, ConversionEventType

@receiver(post_save, sender=Lead)
def handle_lead_save(sender, lead, created, **kwargs) -> None:
    """
    This function is called when a lead record is saved.
    It checks if the call_from (lead phone number) and call_to (call tracking number) match in the phone call table.
    If there's a match, it assigns campaign-level data associated with that call tracking number to the marketing table & reports conv to appropriate ad platform.
    """
    if created:
        try:
            # Step 1: Query the phone call table for any phone calls made by this number
            phone_call = PhoneCall.objects.filter(call_from=lead.phone_number, date_created__lt=lead.created_at).first()

            # Step 2: Retrieve call tracking data
            tracking_call = CallTracking.objects.filter(phone_number=phone_call.call_to).first()

            # Step 3: Assign default conversion event type
            conversion_event_type = ConversionEventType.FormSubmission

            if tracking_call and (phone_call.date_created <= tracking_call.date_expires):
                
                # Step 4: Assign campaign data from tracking call
                lead.lead_marketing = LeadMarketing(
                    click_id=tracking_call.click_id,
                    client_id=tracking_call.client_id,
                    marketing_campaign=tracking_call.call_tracking_number.marketing_campaign,
                )

                # Step 5: Assign website call as event type
                conversion_event_type = ConversionEventType.WebsiteCall
            
            report_conversion(conversion_event_type=conversion_event_type, lead=lead)
        except Exception as e:
            print(f"Error processing lead save: {str(e)}")