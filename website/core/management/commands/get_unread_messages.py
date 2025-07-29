import json
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse

from core.models import Message
from core.email import email_service
from website import settings

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            unread_messages = Message.objects.filter(is_read=False).count()

            if unread_messages > 0:
                email_service.send_email(
                    to=settings.COMPANY_EMAIL,
                    subject=f'{unread_messages} UNREAD MESSAGES',
                    body=f'<a href="{reverse("chat")}">View unread messages</a>'
                )
        except Exception as e:
            raise CommandError(f'Error retrieving unread messages: {e}')