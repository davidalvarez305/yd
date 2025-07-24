from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.billing import billing_service

@csrf_exempt
@require_POST
def handle_payment_webhook(request):
    return billing_service.handle_payment_webhook(request=request)

@require_POST
def handle_initiate_payment(request):
    return billing_service.handle_initiate_payment(request=request)