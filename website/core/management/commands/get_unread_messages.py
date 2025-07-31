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

            chat_url = settings.ROOT_DOMAIN + reverse("chat")

            html = f"""
                <html>
                <body>
                    <p>You have <strong>{unread_messages}</strong> unread messages.</p>
                    <p><a href="{chat_url}">View unread messages</a></p>
                </body>
                </html>
            """

            email_service.send_html_email(
                to=settings.COMPANY_EMAIL,
                subject=f'{unread_messages} UNREAD MESSAGES',
                html=html
            )
        except Exception as e:
            raise CommandError(f'Error retrieving unread messages: {e}')