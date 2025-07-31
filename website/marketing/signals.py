import json
from django.dispatch import receiver
from django.db.models.signals import Signal
from django.db.models import Q
from django.utils.timezone import now

from core.conversions import conversion_service
from core.models import CallTrackingNumber, Lead, LeadStatusHistory

lead_status_changed = Signal()

def create_data_dict(lead: Lead, event_name=None, event=None):
    """
    Creates the data dictionary used to report marketing funnel events.
    """
    data = {
        'created_at': lead.created_at,
        'event_name': event_name,
        'ip_address': lead.lead_marketing.ip,
        'user_agent': lead.lead_marketing.user_agent,
        'event_time': int(now().timestamp()),
        'phone_number': lead.phone_number,
    }

    if event_name == 'event_booked' and event:
        data.update({
            'event_id': event.pk,
            'value': event.amount,
        })

    # Add other attributes to the data dict
    attributes = [
        'client_id',
        'click_id',
        'instant_form_lead_id',
        'landing_page',
    ]
    
    for attr in attributes:
        val = getattr(lead.lead_marketing, attr, None)
        if val:
            data[attr] = val
    
    return data

@receiver(lead_status_changed)
def handle_lead_status_change(sender, instance: Lead, **kwargs):
    """
    This function is called when a lead status is saved.
    This function is used to report marketing funnel events.
    """
    from core.models import LeadMarketing, LeadStatusEnum, PhoneCall, CallTracking
    lead_marketing = LeadMarketing.objects.get(lead=instance)

    # Report Conversion Event
    status_event_map = {
        'LEAD_CREATED': 'generate_lead',
        'INVOICE_SENT': 'invoice_sent',
        'EVENT_BOOKED': 'event_booked',
        'RE_ENGAGED': 're_engaged',
    }

    event = kwargs.get('event')
    lead_status = instance.lead_status
    event_name = status_event_map.get(lead_status.status)

    if not event_name:
        raise ValueError('Invalid event name from lead status.')

    # Assign lead marketing data if lead came from phone call and the lead was just created
    if not lead_marketing.is_instant_form_lead() and lead_status.status == LeadStatusEnum.LEAD_CREATED:
        first_call = PhoneCall.objects.filter(
            Q(call_from=instance.phone_number) | Q(call_to=instance.phone_number)
        ).filter(
            date_created__lt=instance.created_at
        ).order_by('date_created').first()

        if first_call and first_call.is_inbound:
            call_tracking_number = CallTrackingNumber.objects.filter(phone_number=first_call.call_to).first()

            if call_tracking_number:
                tracking_call = (
                    CallTracking.objects
                    .filter(
                        call_tracking_number=call_tracking_number,
                        date_assigned__lt=first_call.date_created,
                        date_expires__gt=first_call.date_created,
                    )
                    .order_by('date_assigned')
                    .first()
                )

                if tracking_call and tracking_call.metadata:
                    metadata = tracking_call.metadata
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except json.JSONDecodeError:
                            metadata = {}

                    if isinstance(metadata, dict):
                        model_fields = {f.name for f in LeadMarketing._meta.fields}

                        for key, value in metadata.items():
                            if key in model_fields:
                                setattr(lead_marketing, key, value)

                        lead_marketing.save()

    # Now that the marketing data has been assigned, generate the data dict and send conversion
    data = create_data_dict(instance, event_name, event)

    # Always send conversion for LEAD_CREATED and EVENT BOOKED
    if lead_status.status == LeadStatusEnum.LEAD_CREATED or lead_status.status == LeadStatusEnum.EVENT_BOOKED:
        conversion_service.send_conversion(data=data)
    
    # Only need to report invoice sent once
    if lead_status.status == LeadStatusEnum.INVOICE_SENT:
        count = LeadStatusHistory.objects.filter(lead_status=lead_status, lead=instance).count()
        if count == 1:
            conversion_service.send_conversion(data=data)