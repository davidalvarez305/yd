from django.dispatch import receiver
from django.db.models.signals import post_save
from django.urls import reverse

from website import settings
from core.models import Message, User
from core.messaging import messaging_service
from core.utils import format_text_message

receiver(post_save)
def handle_new_lead_notification(sender, instance, created, **kwargs):
    if not created:
        return
    
    users = User.objects.filter(is_admin=True)

    text_content = "NEW LEAD:\n" + settings.ROOT_DOMAIN + reverse('lead_detail', kwargs={'pk': instance.pk})

    for user in users:
        message = Message(
            text=format_text_message(text_content),
            text_from=settings.COMPANY_PHONE_NUMBER,
            text_to=user.forward_phone_number,
            is_inbound=False,
            status='sent',
            is_read=True,
        )
        resp = messaging_service.send_text_message(message=message)
        message.external_id = resp.sid
        message.status = resp.status
        message.save()