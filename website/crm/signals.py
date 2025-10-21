from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import Invoice, Quote, get_primary_invoices
from crm.utils import create_quote_due_date

@receiver(post_save, sender=Quote)
def handle_quote_saved(sender, instance: Quote, created, **kwargs):
    """Triggered when a Quote is created or updated."""
    if created:
        invoice_types = get_primary_invoices()
        full_amount = instance.amount()

        for invoice_type in invoice_types:
            invoice = Invoice(
                quote=instance,
                due_date=create_quote_due_date(event_date=instance.event_date),
                invoice_type=invoice_type,
                amount=full_amount * invoice_type.amount_percentage,
            )
            invoice.save()