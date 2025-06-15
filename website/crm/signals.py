from datetime import timedelta
import uuid
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.urls import reverse

from core.models import Invoice, InvoiceType, InvoiceTypeEnum, LeadStatusEnum, Message, Quote, QuoteService
from core.utils import format_text_message
from core.messaging import messaging_service
from website import settings

def update_quote_invoices(quote: Quote):
    try:
        """Updates invoice amounts when a quote or its services change."""
        amount_due = quote.amount()
        if quote.is_deposit_paid():
            remaining_invoice = quote.invoices.filter(invoice_type__type=InvoiceTypeEnum.REMAINING).first()
            if not remaining_invoice:
                raise Exception('No remaining invoice found.')
            remaining_invoice.amount = amount_due - quote.get_deposit_paid_amount()
            remaining_invoice.save()
        else:
            for invoice in quote.invoices.all():
                invoice.amount = amount_due * invoice.invoice_type.amount_percentage
                invoice.save()
    except Exception as e:
        print(f'ERROR UPDATING QUOTE PRICES: {e}')
        raise Exception('Error updating quote services.')

@receiver(post_save, sender=Quote)
def handle_quote_saved(sender, instance, created, **kwargs):
    """Triggered when a Quote is created or updated."""
    if created:
        handle_create_quote(instance)
    update_quote_invoices(instance)

@receiver(post_save, sender=QuoteService)
def handle_quote_service_saved(sender, instance: QuoteService, created, **kwargs):
    """Triggered when a QuoteService is created or updated."""
    if instance.quote.is_paid_off():
        return
    update_quote_invoices(instance.quote)

@receiver(post_delete, sender=QuoteService)
def handle_quote_service_deleted(sender, instance: QuoteService, **kwargs):
    """Triggered when a QuoteService is deleted."""
    if instance.quote.is_paid_off():
        return
    update_quote_invoices(instance.quote)

def handle_create_quote(quote: Quote):
    invoice_types = InvoiceType.objects.all()
    full_amount = quote.amount()
    due_date = quote.event_date - timedelta(days=2)

    for invoice_type in invoice_types:
        invoice = Invoice(
            quote=quote,
            due_date=due_date,
            invoice_type=invoice_type,
            external_id=uuid.uuid4(),
            amount=full_amount * invoice_type.amount_percentage,
        )
        invoice.save()