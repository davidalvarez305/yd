from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Event, Lead
from core.conversions import conversion_service
from marketing.utils import parse_google_ads_cookie

class Command(BaseCommand):
    help = 'Report offline conversions.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--lead_id',
            required=True,
            help='Primary key of the lead.',
        )
        parser.add_argument(
            '--event_name',
            required=True,
            help='Which conversion event should be reported.',
        )
        parser.add_argument(
            '--event_id',
            help='If the event is event_booked, primary key of the event must be provided.',
        )

    def handle(self, *args, **options):
        lead_id = options['lead_id']
        event_name = options['event_name']
        event_id = options['event_id']

        lead = Lead.objects.get(pk=lead_id)

        if not event_name:
            raise ValueError('There must always be an event name provided.')
        
        event_time = int(timezone.now().timestamp())

        if event_name == 'generate_lead':
            event_time = lead.created_at.timestamp()

        data = {
            'event_name': event_name,
            'ip_address': lead.lead_marketing.ip,
            'user_agent': lead.lead_marketing.user_agent,
            'instant_form_lead_id': lead.lead_marketing.instant_form_lead_id,
            'event_time': event_time,
            'phone_number': lead.phone_number,
            'external_id': str(lead.lead_marketing.external_id),
            'lead_id': lead.pk,
        }

        if event_name == 'event_booked':
            event = Event.objects.get(pk=event_id)
            data.update({
                'event_id': event.pk,
                'value': event.amount,
                'event_time': event.date_created.timestamp()
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
                    cookie_click_id = parse_google_ads_cookie(metadata.value)
                    if cookie_click_id:
                        data['gclid'] = cookie_click_id
            else:
                data[metadata.key] = metadata.value

        try:
            conversion_service.send_conversion(data=data)
        except Exception as e:
            print(f'Error sending conv: {e}')