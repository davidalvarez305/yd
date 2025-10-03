import json
from django.dispatch import receiver
from django.db.models.signals import Signal
from django.utils.timezone import now
from django.conf import settings

from core.conversions import conversion_service
from core.models import LandingPage, LandingPageConversion, Lead, LeadMarketingMetadata, LeadStatusHistory, SessionMapping, TrackingPhoneCall, TrackingPhoneCallMetadata
from marketing.utils import create_ad_from_params, generate_params_dict_from_url, parse_google_ads_cookie
from core.utils import get_session_data

lead_status_changed = Signal()

def create_data_dict(lead: Lead, event_name=None, event=None):
    """
    Creates the data dictionary used to report marketing funnel events.
    """
    data = {
        'event_name': event_name,
        'ip_address': lead.lead_marketing.ip,
        'user_agent': lead.lead_marketing.user_agent,
        'instant_form_lead_id': lead.lead_marketing.instant_form_lead_id,
        'event_time': int(now().timestamp()),
        'phone_number': lead.phone_number,
        'external_id': str(lead.lead_marketing.external_id)
    }

    if event_name == 'event_booked' and event:
        data.update({
            'event_id': event.pk,
            'value': event.amount,
        })

    for metadata in lead.lead_marketing.metadata.all():
        if metadata.key == '_fbc':
            data['fbc'] = metadata.value
        elif metadata.key == '_fbp':
            data['fbp'] = metadata.value
        elif metadata.key == '_ga':
            data['ga'] = metadata.value
        elif metadata.key == 'gclid':
            data['gclid'] = metadata.value
        elif metadata.key == 'gbraid':
            data['gbraid'] = metadata.value
        elif metadata.key == 'wbraid':
            data['wbraid'] = metadata.value
        elif metadata.key == '_gcl_aw':
            if 'gclid' not in data:
                data['gclid'] = parse_google_ads_cookie(metadata.value)
        else:
            data[metadata.key] = metadata.value
        
    return data

@receiver(lead_status_changed)
def handle_lead_status_change(sender, instance: Lead, **kwargs):
    """
    This function is called when a lead status is saved.
    This function is used to report marketing funnel events.
    """
    from core.models import LeadMarketing, LeadStatusEnum
    lead_marketing = LeadMarketing.objects.get(lead=instance)

    # Report Conversion Event
    status_event_map = {
        'LEAD_CREATED': 'generate_lead',
        'INVOICE_SENT': 'invoice_sent',
        'EVENT_BOOKED': 'event_booked',
    }

    event = kwargs.get('event')
    lead_status = instance.lead_status
    event_name = status_event_map.get(lead_status.status)

    if not event_name:
        return
    
    # Attach marketing metadata
    last_inbound_call = TrackingPhoneCall.objects.filter(call_from=instance.phone_number).order_by('-date_created').first()

    if last_inbound_call and lead_status.status == LeadStatusEnum.LEAD_CREATED:
        phone_call_metadata = TrackingPhoneCallMetadata.objects.filter(tracking_phone_call=last_inbound_call)

        metadata = phone_call_metadata.filter(key="custom").first()

        if metadata:
            try:
                params = json.loads(metadata.value) or {}

                lp = params.get("calltrk_landing")
                if lp:
                    params |= generate_params_dict_from_url(lp)

                external_id = params.get(settings.TRACKING_COOKIE_NAME)
                if external_id:
                    session_mapping = SessionMapping.objects.filter(external_id=external_id).first()
                    if session_mapping:
                        session = get_session_data(session_key=session_mapping.session_key)

                        lead_marketing.ip = session.get('ip')
                        lead_marketing.user_agent = session.get('user_agent')
                        lead_marketing.external_id = external_id
                        lead_marketing.ad = create_ad_from_params(params=params, cookies=params)
                        lead_marketing.save()
                        lead_marketing.assign_visits()

                        landing_page_id = session.get('landing_page_id')
                        if landing_page_id:
                            landing_page = LandingPage.objects.filter(pk=landing_page_id).first()
                            if landing_page:
                                conversion = LandingPageConversion(
                                    lead=instance,
                                    landing_page=landing_page,
                                    conversion_type=LandingPageConversion.PHONE_CALL
                                )
                                conversion.save()

                for key, value in params.items():
                    LeadMarketingMetadata.objects.create(
                        key=key,
                        value=value,
                        lead_marketing=lead_marketing,
                    )
            except (TypeError, json.JSONDecodeError):
                print("Failed to load params")

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