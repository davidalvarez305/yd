import stripe
from website import settings
from core.billing.base import BillingServiceInterface

from django.urls import reverse
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.utils.timezone import now

from core.models import Event, Invoice, Lead, LeadStatusEnum, Message, User
from billing.enums import InvoiceTypeChoices
from core.messaging import messaging_service
from website import settings
from core.enums import AlertStatus
from core.utils import default_alert_handler

class StripeBillingService(BillingServiceInterface):
    def __init__(self, api_key: str, webhook_secret: str):
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.alert = default_alert_handler

        stripe.api_key = self.api_key

    def handle_payment_webhook(self, request):
        payload = request.body
        stripe_signature = request.headers.get('Stripe-Signature')

        if not stripe_signature:
            return HttpResponse(status=400) 

        try:
            event = stripe.Webhook.construct_event(payload, stripe_signature, self.webhook_secret)

            if event.get('type') == 'checkout.session.completed':
                session = event.get('data', {}).get('object')

                if not session:
                    raise Exception('Improperly formatted request.')

                session_id = session.id
                external_id = session.get('metadata', {}).get('external_id')

                invoice = Invoice.objects.filter(external_id=external_id, session_id=session_id).first()
                if not invoice:
                    raise Exception('Could not find invoice in database.')

                invoice.date_paid = now()
                invoice.save()

                # Create event on successful payment
                if invoice.invoice_type.type in [InvoiceTypeChoices.DEPOSIT.value, InvoiceTypeChoices.FULL.value]:
                    lead = invoice.quote.lead
                    event = Event(
                        lead=lead,
                        date_paid=now(),
                        amount=invoice.quote.amount(),
                        guests=invoice.quote.guests,
                    )
                    event.save()

                    # Report conversion
                    lead.change_lead_status(LeadStatusEnum.EVENT_BOOKED)

                    # Notify via text messages
                    admins = User.objects.filter(is_superuser=True)
                    for user in admins:
                        try:
                            text = "\n".join([
                                f"EVENT BOOKED:",
                                f"Date: {invoice.quote.event_date.strftime('%b %d, %Y')}",
                                f"Full Name: {invoice.quote.lead.full_name}"
                            ])

                            message = Message(
                                text=text,
                                text_from=settings.COMPANY_PHONE_NUMBER,
                                text_to=user.forward_phone_number,
                                is_inbound=False,
                                status='sent',
                                is_read=True,
                            )
                            message.save()

                            messaging_service.send_text_message(message)
                        except Exception as e:
                            return self.alert(request=self.request, message=str(e), status=AlertStatus.INTERNAL_ERROR, reswap=True)

            return HttpResponse(status=200)

        except Exception as e:
            return self.alert(request=self.request, message=str(e), status=AlertStatus.INTERNAL_ERROR, reswap=True)

    def handle_initiate_payment(self, request):
        lead_id = request.GET.get('lead_id')
        invoice_id = request.GET.get('invoice_id')

        if not lead_id or not invoice_id:
            return self.alert(request=self.request, message="Missing lead_id or invoice_id.", status=AlertStatus.BAD_REQUEST, reswap=True)
        
        lead = Lead.objects.filter(pk=lead_id).first()
        invoice = Invoice.objects.filter(pk=invoice_id).first()

        if invoice.date_paid is not None:
            return self.alert(request=self.request, message="Invoice already paid, cannot initiate session.", status=AlertStatus.BAD_REQUEST, reswap=True)

        if not lead or not invoice:
            return self.alert(request=self.request, message="Could not query lead or invoice.", status=AlertStatus.BAD_REQUEST, reswap=True)

        try:
            session = stripe.checkout.Session.create(
                line_items=[
                    {
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': f'Invoice #{invoice.external_id}',
                            },
                            'unit_amount': int(invoice.amount * 100),
                        },
                        'quantity': 1,
                    }
                ],
                mode='payment',
                ui_mode='hosted',
                success_url=settings.ROOT_DOMAIN + reverse('success_payment', kwargs={'external_id': str(invoice.external_id)}),
                cancel_url=settings.ROOT_DOMAIN + reverse('cancel_payment', kwargs={'external_id': str(invoice.external_id)}),
                metadata={
                    'external_id': str(invoice.external_id),
                },
            )
            invoice.session_id = session.id
            invoice.save()

            return HttpResponse(status=200, headers={ "HX-Redirect": session.url })
        except Exception as e:
            print(f'FAILED TO INITIATE PAYMENT: {e}')
            return self.alert(request=self.request, message="Failed to initiate payment.", status=AlertStatus.INTERNAL_ERROR, reswap=True)