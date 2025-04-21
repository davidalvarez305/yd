from django.views.decorators.csrf import csrf_exempt

from .messaging import MessagingService
from .enums import MessagingProvider

@csrf_exempt
def handle_inbound_message(request):
    service = MessagingService(MessagingProvider.TWILIO)

    return service.handle_inbound_message(request)