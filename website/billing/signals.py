from datetime import timedelta
import uuid
from django.urls import reverse
import stripe
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Invoice, InvoiceType, InvoiceTypeEnum, Quote

@receiver(post_save, sender=Quote)
def quote_created_or_updated(sender, instance, created, **kwargs):
    if created:
        invoice_types = InvoiceType.objects.all()
        full_amount = instance.amount() * 100
        due_date = instance.event_date - timedelta(hours=48)

        for invoice_type in invoice_types:
            invoice_amount = full_amount * invoice_type.amount_percentage * 100
            invoice_external_id = uuid.uuid4()

            invoice = Invoice(
                quote=instance,
                due_date=due_date,
                invoice_type=invoice_type,
                external_id=invoice_external_id,
                amount=invoice_amount,
            )
            invoice.save()
    else:
        new_amount = instance.amount()
        deposit_invoice = instance.invoices.filter(invoice_type==InvoiceTypeEnum.DEPOSIT).first()
        if deposit_invoice.date_paid:
            remaining_invoice = instance.invoices.filter(invoice_type==InvoiceTypeEnum.REMAINING).first()
            remaining_invoice.amount_due = new_amount - deposit_invoice.amount_due
            remaining_invoice.save()
        else:
            for invoice in instance.invoices.all():
                invoice.amount = new_amount * invoice.invoice_type.amount_percentage
                invoice.save()