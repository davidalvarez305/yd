from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.urls import reverse

from core.models import InvoiceTypeEnum, Message, Quote, QuoteService
from core.utils import format_text_message
from core.messaging import messaging_service
from website import settings

def update_quote_invoices(quote: Quote):
    """Updates invoice amounts when a quote or its services change."""
    new_amount = quote.amount()
    if quote.is_deposit_paid():
        remaining_invoice = quote.invoices.filter(invoice_type=InvoiceTypeEnum.REMAINING).first()
        if remaining_invoice:
            remaining_invoice.amount = new_amount - quote.get_deposit_paid_amount()
            remaining_invoice.save()
    else:
        for invoice in quote.invoices.all():
            invoice.amount = new_amount * invoice.invoice_type.amount_percentage
            invoice.save()

@receiver(post_save, sender=Quote)
def handle_quote_saved(sender, instance, created, **kwargs):
    """Triggered when a Quote is created or updated."""
    if created:
        handle_create_quote(instance)
    else:
        update_quote_invoices(instance)

@receiver(post_save, sender=QuoteService)
def handle_quote_service_saved(sender, instance, created, **kwargs):
    """Triggered when a QuoteService is created or updated."""
    update_quote_invoices(instance.quote)

@receiver(post_delete, sender=QuoteService)
def handle_quote_service_deleted(sender, instance, **kwargs):
    """Triggered when a QuoteService is deleted."""
    update_quote_invoices(instance.quote)

@receiver(post_save, sender=Quote)
def handle_create_quote(sender, instance: Quote, created, **kwargs):
    if created:
        text_content = 'BARTENDING QUOTE:\n' + settings.ROOT_DOMAIN + reverse('external_quote_detail', kwargs={ 'external_id': instance.external_id })
        message = Message(
                text=format_text_message(text_content),
                text_from=settings.COMPANY_PHONE_NUMBER,
                text_to=instance.lead.phone_number,
                is_inbound=False,
                status='sent',
                is_read=True,
            )
        resp = messaging_service.send_text_message(message=message)
        message.external_id = resp.sid
        message.status = resp.status
        message.save()