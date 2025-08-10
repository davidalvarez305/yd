from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse

from core.models import Message
from core.email import email_service
from website import settings

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            unread_messages = Message.objects.filter(is_read=False, is_notified=False)
            count = unread_messages.count()

            if count == 0:
                return

            chat_url = settings.ROOT_DOMAIN + reverse("chat")

            html = f"""
                <html>
                <body>
                    <p>You have <strong>{count}</strong> unread messages.</p>
                    <p><a href="{chat_url}">View unread messages</a></p>
                </body>
                </html>
            """

            email_service.send_html_email(
                to=settings.COMPANY_EMAIL,
                subject=f'{count} UNREAD MESSAGES',
                html=html
            )

            unread_messages.update(is_notified=True)

        except Exception as e:
            raise CommandError(f'Error retrieving unread messages: {e}')