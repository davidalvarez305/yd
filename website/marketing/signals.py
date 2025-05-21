from django.dispatch import receiver

from core.conversions import conversion_service
from core.models import Lead, LeadMarketing, MarketingCampaign, PhoneCall
from core.models import CallTracking
from core.signals import lead_status_changed

@receiver(lead_status_changed)
def handle_lead_status_change(sender, instance: Lead, **kwargs):
    """
    This function is called when a lead status is saved.
    This function is used to report marketing funnel events.
    """
    print(f"[DEBUG] Handling lead status change for Lead ID: {instance.pk}, Status: {instance.lead_status.status}")

    lead_marketing = LeadMarketing.objects.filter(lead=instance).first()
    print(f"[DEBUG] Retrieved LeadMarketing: {lead_marketing}")

    if not lead_marketing:
        print("[ERROR] Lead marketing not found.")
        raise ValueError('Lead marketing not found.')

    if lead_marketing.is_instant_form_lead():
        print("[DEBUG] Lead is an instant form lead, skipping.")
        return

    first_inbound_call = PhoneCall.objects.filter(call_from=instance.phone_number).order_by('date_created').first()
    print(f"[DEBUG] First inbound call: {first_inbound_call}")

    if not first_inbound_call:
        print("[DEBUG] No inbound call found, skipping tracking.")
        return

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

    print(f"[DEBUG] Tracking call: {tracking_call}")

    if not tracking_call:
        print("[DEBUG] No matching CallTracking found.")
        return
    
    for key, value in tracking_call.metadata.items():
        if hasattr(lead_marketing, key):
            print(f"[DEBUG] Setting attribute on LeadMarketing: {key} = {value}")
            setattr(lead_marketing, key, value)

    campaign_id = tracking_call.metadata.get('marketing_campaign_id')
    campaign_name = tracking_call.metadata.get('marketing_campaign_name')
    print(f"[DEBUG] Campaign ID: {campaign_id}, Campaign Name: {campaign_name}")

    if campaign_id and campaign_name:
        campaign, created = MarketingCampaign.objects.get_or_create(
            marketing_campaign_id=campaign_id,
            platform_id=lead_marketing.platform_id,
            defaults={'name': campaign_name}
        )
        print(f"[DEBUG] Campaign {'created' if created else 'retrieved'}: {campaign}")
        lead_marketing.marketing_campaign = campaign

    lead_marketing.save()
    print(f"[DEBUG] LeadMarketing updated and saved: {lead_marketing.pk}")

    status_event_map = {
        'Lead Created': 'generate_lead',
        'Qualified Lead': 'qualified_lead',
        'Sales Prospect': 'invoice_sent',
        'Event Booking': 'event_booked',
    }

    event_name = status_event_map.get(instance.lead_status.status)
    print(f"[DEBUG] Mapped event name: {event_name}")

    if not event_name:
        print("[ERROR] Invalid event name from lead status.")
        raise ValueError('Invalid event name from lead status.')
    
    data = {
        'event_name': event_name,
        'ip_address': lead_marketing.ip,
        'user_agent': lead_marketing.user_agent,
        'event_time': instance.created_at,
    }

    value = instance.value()
    if value > 0.0:
        data['value'] = value
        data['currency'] = 'USD'
        print(f"[DEBUG] Event has monetary value: {value} USD")

    attributes = ['client_id', 'click_id', 'email', 'phone_number']
    for attr in attributes:
        attr_value = getattr(lead_marketing, attr, None)
        if attr_value:
            data[attr] = attr_value
            print(f"[DEBUG] Added to data: {attr} = {attr_value}")

    print(f"[DEBUG] Sending conversion data: {data}")
    conversion_service.send_conservion(data=data)
