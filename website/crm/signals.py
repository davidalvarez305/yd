from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from website import settings

from core.models import EventStatusChoices, EventStatusHistory, Invoice, Quote, get_primary_invoices
from core.email import email_service
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

@receiver(post_save, sender=EventStatusHistory)
def handle_event_status_change(sender, instance: EventStatusHistory, created, **kwargs):
    status = instance.event_status.status

    if status == EventStatusChoices.BOOKED:
        event_details = settings.ROOT_DOMAIN + reverse("event_detail", kwargs={ 'pk': instance.event.pk })
        html = f"""
            <html>
            <body>
                <p><a href="{event_details}">View Event Details</a></p>
            </body>
            </html>
        """
        
        email_service.send_html_email(
            to=settings.COMPANY_EMAIL,
            subject=f"Finalize {instance.event.lead.full_name}'s Event Details",
            html=html
        )

        instance.event.change_event_status(EventStatusChoices.ONBOARDING)

    return