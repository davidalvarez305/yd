from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Event, Lead
from core.conversions import conversion_service

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

        data = {}

        if not event_name:
            raise ValueError('There must always be an event name provided.')

        data = {
            'event_name': event_name,
            'ip_address': lead.lead_marketing.ip,
            'user_agent': lead.lead_marketing.user_agent,
            'event_time': int(timezone.now().timestamp()),
        }

        if event_name == 'event_booked':
            event = Event.objects.get(pk=event_id)
            data.update({
                'event_id': event.pk,
                'value': event.amount,
            })

        attributes = [
            'client_id',
            'click_id',
            'phone_number',
            'instant_form_lead_id'
        ]

        for attr in attributes:
            val = getattr(lead.lead_marketing, attr)
            if val:
                data[attr] = val

        print(f'Sending conversion for: {data}')
        return
        try:
            conversion_service.send_conversion(data=data)
        except Exception as e:
            print(f'Error sending conv: {e}')