from django.dispatch import receiver

from core.conversions import conversion_service
from core.models import Lead, LeadMarketing, LeadStatusEnum, MarketingCampaign, PhoneCall
from core.models import CallTracking
from core.signals import lead_status_changed

@receiver(lead_status_changed)
def handle_lead_status_change(sender, instance: Lead, **kwargs):
    """
    This function is called when a lead status is saved.
    This function is used to report marketing funnel events.
    """
    lead_marketing = LeadMarketing.objects.filter(lead=instance).first()

    if not lead_marketing:
        raise ValueError('Lead marketing not found.')
    
    # Report Conversion Event
    status_event_map = {
        'Lead Created': 'generate_lead',
        'Sales Prospect': 'invoice_sent',
        'Event Booking': 'event_booked',
    }

    event_name = status_event_map.get(instance.lead_status.status)

    if not event_name:
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

    attributes = [
        'client_id',
        'click_id',
        'email',
        'phone_number',
        'instant_form_lead_id'
    ]

    for attr in attributes:
        attr_value = getattr(lead_marketing, attr, None)
        if attr_value:
            data[attr] = attr_value

    conversion_service.send_conservion(data=data)

    # Assign lead marketing data if lead came from phone call
    if lead_marketing.is_instant_form_lead():
        return
    
    # Only apply marketing data the first time the lead is assigned to lead created
    if instance.lead_status.status != LeadStatusEnum.LEAD_CREATED:
        return

    first_inbound_call = PhoneCall.objects.filter(call_from=instance.phone_number).order_by('date_created').first()

    if not first_inbound_call:
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

    if not tracking_call:
        return
    
    for key, value in tracking_call.metadata.items():
        if hasattr(lead_marketing, key):
            setattr(lead_marketing, key, value)

    campaign_id = tracking_call.metadata.get('marketing_campaign_id')
    campaign_name = tracking_call.metadata.get('marketing_campaign_name')

    if campaign_id and campaign_name:
        campaign, _ = MarketingCampaign.objects.get_or_create(
            marketing_campaign_id=campaign_id,
            platform_id=lead_marketing.platform_id,
            defaults={'name': campaign_name}
        )
        lead_marketing.marketing_campaign = campaign

    lead_marketing.save()
