from django.core.management.base import BaseCommand, CommandError
from core.models import Lead
from core.conversions import conversion_service


class Command(BaseCommand):
    help = 'Retract an offline conversion by conversion ID.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--lead_id',
            required=True,
            help='Primary key of the lead.',
        )
        parser.add_argument(
            '--event_name',
            required=True,
            help='Conversion event name (must match the original conversion).',
        )
        parser.add_argument(
            '--event_id',
            required=False,
            help='Order ID (required for event_booked).',
        )

    def handle(self, *args, **options):
        lead_id = options['lead_id']
        event_id = options['event_id']
        event_name = options['event_name']

        if event_name == "event_booked" and not event_id:
            raise CommandError("--event_id is required when --event_name=event_booked")

        lead = Lead.objects.select_related('lead_marketing').prefetch_related('lead_marketing__metadata').get(pk=lead_id)

        if not event_name:
            raise ValueError('There must always be an event name provided.')

        data = {
            'event_name': event_name,
            'event_id': event_id,
            'external_id': str(lead.lead_marketing.external_id),
            'phone_number': lead.phone_number,
            'ip_address': lead.lead_marketing.ip,
            'user_agent': lead.lead_marketing.user_agent,
            'event_time': lead.created_at.timestamp()
        }

        for metadata in lead.lead_marketing.metadata.all():
            data[metadata.key] = metadata.value

        try:
            conversion_service.retract_conversion(data=data)
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Error retracting conversion: {e}')
            )