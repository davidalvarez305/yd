from django.core.management.base import BaseCommand

from core.messaging import messaging_service
from core.models import Message

class Command(BaseCommand):
    help = 'Fetch Twilio messages and either save to DB or export to JSON.'

    def handle(self, *args, **options):
        messages = messaging_service.get_all_messages()

        for msg in messages:
            sid = msg.get('sid')
            message = Message.objects.filter(external_id=sid).first()
            if message:
                message.date_created = msg.get('date_created')
                message.save()