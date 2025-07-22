import json

from django.core.management.base import BaseCommand

from core.messaging import messaging_service
from core.models import Message

class Command(BaseCommand):
    help = 'Fetch Twilio messages and either save to DB or export to JSON.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--save',
            action='store_true',
            help='Save messages to the database'
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Export messages to data.json'
        )

    def handle(self, *args, **options):
        messages = messaging_service.get_all_messages()

        if options['json']:
            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
            self.stdout.write(self.style.SUCCESS(f"✅ Exported {len(messages)} messages to data.json"))

        if options['save']:
            count = 0
            for msg in messages:
                try:
                    message = Message.objects.get(external_id=msg.get('sid'))
                    if message:
                        message.date_created = msg.get('date_created')
                    message.save()
                    count += 1

                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"❌ Failed to process message {msg.get('sid')}: {e}"))
                    continue

            self.stdout.write(self.style.SUCCESS(f"✅ Successfully saved {count} messages to the database"))