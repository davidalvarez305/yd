import stripe

from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.timezone import now

from core.models import Event, Invoice, Lead, LeadStatusEnum, Message, User
from billing.enums import InvoiceTypeChoices
from core.messaging import messaging_service
from website import settings

stripe.api_key = settings.STRIPE_API_KEY
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET

@csrf_exempt
@require_POST
def handle_stripe_invoice_payment(request):
    payload = request.body
    stripe_signature = request.META.get('HTTP_STRIPE_SIGNATURE')

    if not stripe_signature:
        return HttpResponse(status=400) 

    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, STRIPE_WEBHOOK_SECRET)

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
            if invoice.invoice_type in [InvoiceTypeChoices.DEPOSIT, InvoiceTypeChoices.FULL]:
                lead = invoice.quote.lead
                event = Event(
                    lead=lead,
                    date_created=now(),
                    date_paid=now(),
                    amount=invoice.quote.amount(),
                    guests=invoice.quote.guests,
                )
                event.save()

				# Report conversion
                lead.change_lead_status(LeadStatusEnum.EVENT_BOOKED)

                # Notify via text messages
                admins = User.objects.filter(is_admin=True)
                notify_list = [lead.phone_number] + [admin.forward_phone_number for admin in admins]
                for phone_number in notify_list:
                    try:
                        text = (
                            f"EVENT BOOKED:\n\nDate: {invoice.quote.event_date.strftime('%b %d, %Y')},\nFull Name: {invoice.quote.full_name}"
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

@login_required
@require_POST
def handle_initiate_checkout(request):
    lead_id = request.POST.get('lead_id')
    invoice_id = request.POST.get('invoice_id')

    if not lead_id or not invoice_id:
        return HttpResponseBadRequest("Missing lead_id or invoice_id.")
    
    lead = Lead.objects.filter(pk=lead_id).first()
    invoice = Invoice.objects.filter(pk=invoice_id).first()

    if not lead or not invoice:
        return HttpResponseBadRequest("Could not query lead or invoice.")

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
        )
        invoice.session_id = session.id
        invoice.save()

        return HttpResponse(status=200, headers={ "HX-Redirect": session.url })
    except Exception as e:
        print(f'ERROR: {e}')
        return HttpResponseServerError(f"Unexpected error.")