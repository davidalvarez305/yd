from django.dispatch import receiver
from django.db.models.signals import Signal
from django.utils.timezone import now
from django.db.models import Q

from core.conversions import conversion_service
from core.models import LeadStatusHistory

lead_status_changed = Signal()

@receiver(lead_status_changed)
def handle_lead_status_change(sender, instance, **kwargs):
    """
    This function is called when a lead status is saved.
    This function is used to report marketing funnel events.
    """
    from core.models import LeadMarketing, LeadStatusEnum, MarketingCampaign, PhoneCall, CallTracking
    lead_marketing = LeadMarketing.objects.filter(lead=instance).first()

    if not lead_marketing:
        raise ValueError('Lead marketing not found.')
    
    # Report Conversion Event
    status_event_map = {
        'LEAD_CREATED': 'generate_lead',
        'INVOICE_SENT': 'invoice_sent',
        'EVENT_BOOKED': 'event_booked',
        'RE_ENGAGED': 're_engaged',
    }

    event_name = status_event_map.get(instance.lead_status.status)

    if not event_name:
        raise ValueError('Invalid event name from lead status.')
    
    data = {
        'event_name': event_name,
        'ip_address': lead_marketing.ip,
        'user_agent': lead_marketing.user_agent,
        'event_time': int(now().timestamp()),
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

    status_counts = LeadStatusHistory.objects.filter(
        Q(lead_status__status=LeadStatusEnum.INVOICE_SENT) |
        Q(lead_status__status=LeadStatusEnum.EVENT_BOOKED)
    ).count()

    if instance.lead_status.status != LeadStatusEnum.RE_ENGAGED and status_counts == 0:
        conversion_service.send_conversion(data=data)

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
            defaults={'name': campaign_name}
        )
        lead_marketing.marketing_campaign = campaign

    lead_marketing.save()
