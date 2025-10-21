import requests
import stripe
from website import settings
from core.billing.base import BillingServiceInterface

from django.urls import reverse
from django.http import HttpResponse
from django.utils import timezone
from django.core.files.base import ContentFile

from core.models import Event, Invoice, Lead, Message, User
from billing.enums import InvoiceTypeChoices
from core.messaging import messaging_service
from core.enums import AlertStatus
from core.utils import default_alert_handler
from core.logger import logger
from core.managers.event import EventManager

class StripeBillingService(BillingServiceInterface):
    def __init__(self, api_key: str, webhook_secret: str):
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.alert = default_alert_handler
        self.phone_numbers = [u.forward_phone_number for u in User.objects.filter(is_superuser=True)]

        stripe.api_key = self.api_key

    def handle_payment_webhook(self, request):
        payload = request.body
        stripe_signature = request.headers.get('Stripe-Signature')

        if not stripe_signature:
            return HttpResponse(status=400)

        try:
            event = stripe.Webhook.construct_event(payload, stripe_signature, self.webhook_secret)
            event_type = event.get('type')
            data = event.get('data', {}).get('object')

            if event_type == 'checkout.session.completed':
                return self._handle_checkout_completed(data)

            if event_type == 'charge.updated':
                return self._handle_charge_updated(data)

            return HttpResponse(status=200)

        except Exception as e:
            logger.exception(str(e), exc_info=True)
            return HttpResponse(status=500)

    def _handle_checkout_completed(self, session):
        try:
            session_id = session.get('id')
            external_id = session.get('metadata', {}).get('external_id')
            now = timezone.now()

            if not session_id or not external_id:
                return HttpResponse(status=400)

            invoice = Invoice.objects.filter(external_id=external_id, session_id=session_id).first()
            if not invoice:
                return HttpResponse(status=404)

            if not invoice.date_paid:
                invoice.date_paid = now
                invoice.save()

            if invoice.invoice_type.type in [InvoiceTypeChoices.DEPOSIT.value, InvoiceTypeChoices.FULL.value]:
                event = Event.objects.create(
                    lead=invoice.quote.lead,
                    date_paid=now,
                    amount=invoice.quote.amount(),
                    guests=invoice.quote.adults + invoice.quote.minors,
                    quote=invoice.quote,
                )

                event_manager = EventManager(event=event)
                event_manager.book()
        except Exception as e:
            logger.exception(str(e), exc_info=True)
            return HttpResponse(status=500)

        return HttpResponse(status=200)

    def _handle_charge_updated(self, charge):
        if not (charge.get("paid") and charge.get("status") == "succeeded"):
            return HttpResponse(status=200)

        payment_intent_id = charge.get("payment_intent")
        if not payment_intent_id:
            return HttpResponse(status=200)

        try:
            sessions = stripe.checkout.Session.list(payment_intent=payment_intent_id, limit=1).get('data', [])
            if not sessions:
                return HttpResponse(status=200)

            session = sessions[0]
            external_id = session.get('metadata', {}).get('external_id')
            session_id = session.get('id')

            if not external_id or not session_id:
                return HttpResponse(status=200)

            invoice = Invoice.objects.filter(external_id=external_id, session_id=session_id).first()
            if not invoice:
                return HttpResponse(status=200)

            receipt_url = charge.get("receipt_url")
            if receipt_url:
                try:
                    response = requests.get(receipt_url)
                    if response.status_code == 200:
                        filename = f"{invoice.external_id}.html"
                        invoice.receipt.save(filename, ContentFile(response.content), save=True)

                        users_to_notify = list(self.phone_numbers)
                        users_to_notify.append(invoice.quote.lead.phone_number)

                        for phone_number in users_to_notify:
                            message = Message(
                                text=f"RECEIPT: {invoice.receipt.url}",
                                text_from=settings.COMPANY_PHONE_NUMBER,
                                text_to=phone_number,
                                is_inbound=False,
                                status='sent',
                                is_read=True,
                            )
                            response = messaging_service.send_text_message(message)
                            message.external_id = response.sid
                            message.save()
                except Exception as e:
                    print(f"Receipt download failed: {e}")
                    return HttpResponse(status=500)

        except Exception as e:
            print(f"Charge.updated processing failed: {e}")
            logger.exception(str(e), exc_info=True)
            return HttpResponse(status=500)

        return HttpResponse(status=200)

    def handle_initiate_payment(self, request):
        lead_id = request.GET.get('lead_id')
        invoice_id = request.GET.get('invoice_id')

        if not lead_id or not invoice_id:
            return self.alert(request=request, message="Missing lead_id or invoice_id.", status=AlertStatus.BAD_REQUEST, reswap=True)

        lead = Lead.objects.filter(pk=lead_id).first()
        invoice = Invoice.objects.filter(pk=invoice_id).first()

        if not lead or not invoice:
            return self.alert(request=request, message="Could not query lead or invoice.", status=AlertStatus.BAD_REQUEST, reswap=True)

        if invoice.date_paid is not None:
            return self.alert(request=request, message="Invoice already paid, cannot initiate session.", status=AlertStatus.BAD_REQUEST, reswap=True)

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

            return HttpResponse(status=200, headers={"HX-Redirect": session.url})
        except Exception as e:
            return self.alert(request=request, message="Failed to initiate payment.", status=AlertStatus.INTERNAL_ERROR, reswap=True)