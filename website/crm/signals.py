from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.models import InvoiceTypeEnum, Quote, QuoteService

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
        create_invoices_for_quote(instance)
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