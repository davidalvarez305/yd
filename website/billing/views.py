import stripe
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils.timezone import now

from core.models import Event, Invoice, LeadStatusEnum, Message, User
from billing.enums import InvoiceTypeChoices
from core.messaging import messaging_service

stripe.api_key = settings.STRIPE_API_KEY
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET

@csrf_exempt
def handle_stripe_invoice_payment(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)

        if event['type'] == 'invoice.payment_succeeded':
            invoice_data = event['data']['object']
            stripe_invoice_id = invoice_data.get('id')

            invoice = Invoice.objects.filter(stripe_invoice_id=stripe_invoice_id).first()
            if not invoice:
                raise Exception('Could not find invoice by stripe invoice id in database.')

            invoice.date_paid = now()
            invoice.save()

			# Create event on successful payment
            if invoice.invoice_type in [InvoiceTypeChoices.DEPOSIT, InvoiceTypeChoices.FULL]:
                event = Event(
                    lead=invoice.quote.lead,
                    date_created=now(),
                    date_paid=now(),
                    amount=invoice.quote.amount,
                    guests=invoice.quote.guests,
                )
                event.save()

				# Report conversion
                invoice.quote.lead.change_lead_status(LeadStatusEnum.EVENT_BOOKED)

                # Notify via text messages
                admins = User.objects.filter(is_admin=True)
                notify_list = [invoice.quote.lead.phone_number] + [admin.forward_phone_number for admin in admins]
                for phone_number in notify_list:
                    try:
                        text = (
                            f"EVENT BOOKED:\n\nDate: {invoice.quote.event_date.strftime('%b %d, %Y')},\nFull Name: {quote.full_name}"
                        )

                        message = Message(
                            text=text,
                            date_created=now(),
                            text_from=settings.COMPANY_PHONE_NUMBER,
                            text_to=phone_number,
                            is_inbound=False,
                            status='sent',
                            is_read=True,
                        )
                        message.save()

                        messaging_service.send_text_message(phone_number, message)
                    except Exception as e:
                        print(f'Failed to send event booking notification: {str(e)}')
                        continue

        return HttpResponse(status=200)

    except Exception as e:
        return HttpResponse(status=400)