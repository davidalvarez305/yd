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

    if campaign_id and campaign_name:
        lead_marketing.marketing_campaign = MarketingCampaign.objects.get_or_create(
            marketing_campaign_id=campaign_id,
            platform_id=lead_marketing.platform_id,
            name=campaign_name,
        )

    lead_marketing.save()
    
    status_event_map = {
        'Lead Created': 'generate_lead',
        'Qualified Lead': 'qualified_lead',
        'Sales Prospect': 'invoice_sent',
        'Event Booking': 'event_booked',
    }

    event_name = status_event_map.get(instance.lead_status.status)

    if not event_name:
        raise ValueError('Invalid event name from lead status.')
    
    data = {}
    data['event_name'] = event_name
    data['ip_address'] = lead_marketing.ip
    data['user_agent'] = lead_marketing.user_agent
    data['event_time'] = instance.created_at

    value = instance.value()
    if value > 0.0:
        data['value'] = value
        data['currency'] = 'USD'

    attributes = ['client_id', 'click_id', 'email', 'phone_number']
    for attr in attributes:
        value = getattr(lead_marketing, attr, None)
        if value:
            data[attr] = value

    conversion_service.send_conservion(data=data)