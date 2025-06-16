from datetime import timedelta
import uuid
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.models import Invoice, InvoiceType, Quote

@receiver(post_save, sender=Quote)
def handle_quote_saved(sender, instance: Quote, created, **kwargs):
    """Triggered when a Quote is created or updated."""
    if created:
        invoice_types = InvoiceType.get_primary_invoices()
        full_amount = instance.amount()
        due_date = instance.event_date - timedelta(days=2)

        for invoice_type in invoice_types:
            invoice = Invoice(
                quote=instance,
                due_date=due_date,
                invoice_type=invoice_type,
                external_id=uuid.uuid4(),
                amount=full_amount * invoice_type.amount_percentage,
            )
            invoice.save()