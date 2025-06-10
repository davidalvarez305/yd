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
            session = stripe.checkout.Session.create(
                line_items=[
                    {
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': f'Invoice ID: {str(invoice_external_id)}',
                            },
                            'unit_amount': invoice_amount,
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                ui_mode='hosted',
                success_url=reverse('success_payment', kwargs={'external_id': str(invoice_external_id)}),
                cancel_url=reverse('cancel_payment', kwargs={'external_id': str(invoice_external_id)}),
            )

            invoice = Invoice(
                quote=instance,
                due_date=due_date,
                invoice_type=invoice_type,
                external_id=invoice_external_id,
                url=session.url,
            )
            invoice.save()
    else:
        deposit_invoice = instance.invoices.filter(invoice_type==InvoiceTypeEnum.DEPOSIT).first()
        
        for invoice in instance.invoices.all():
            if invoice.date_paid:
                continue

            # adjust prices based on deposit_invoice


