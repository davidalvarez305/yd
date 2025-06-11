from datetime import timedelta
import uuid

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.models import Invoice, InvoiceType, InvoiceTypeEnum, Quote, QuoteService

def create_invoices_for_quote(quote: Quote):
    """Creates deposit and remaining invoices for a new quote."""
    invoice_types = InvoiceType.objects.all()
    full_amount = quote.amount()
    due_date = quote.event_date - timedelta(hours=48)

    for invoice_type in invoice_types:
        invoice_amount = full_amount * invoice_type.amount_percentage
        invoice_external_id = uuid.uuid4()

        Invoice.objects.create(
            quote=quote,
            due_date=due_date,
            invoice_type=invoice_type,
            external_id=invoice_external_id,
            amount=invoice_amount,
        )

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

@receiver(post_save, sender=QuoteService)
def handle_quote_service_saved(sender, instance, created, **kwargs):
    """Triggered when a QuoteService is created or updated."""
    update_quote_invoices(instance.quote)

@receiver(post_delete, sender=QuoteService)
def handle_quote_service_deleted(sender, instance, **kwargs):
    """Triggered when a QuoteService is deleted."""
    update_quote_invoices(instance.quote)