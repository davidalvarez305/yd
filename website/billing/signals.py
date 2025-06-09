import stripe
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Quote

@receiver(post_save, sender=Quote)
def quote_created_or_updated(sender, instance, created, **kwargs):
    if created:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Invoice #{invoice.invoice_id}',
                    },
                    'unit_amount': amount_in_cents,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='https://your-site.com/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://your-site.com/cancel',
        )
    else:
        for service in instance.quote_services.all():
            print('service')
        # adjust invoice price
