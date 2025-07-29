import json
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse

from core.models import Message
from core.email import email_service
from website import settings

class Command(BaseCommand):
    help = 'Fetch and print Facebook lead data for a given leadgen_id using the existing facebook_api_service instance.'

    def handle(self, *args, **options):
        try:
            unread_messages = Message.objects.filter(is_read=False).count()

            if unread_messages > 0:
                email = settings.COMPANY_EMAIL

                email_service.send_email(
                    to=email,
                    subject=f'{unread_messages} UNREAD MESSAGES',
                    body=f'<a href="{reverse("chat")}">View unread messages</a>'
                )
        except Exception as e:
            raise CommandError(f'Error retrieving unread messages: {e}')