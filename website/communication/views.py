from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from .messaging import MessagingService
from .enums import MessagingProvider

@csrf_exempt
def handle_inbound_message(request):
    if request.method != "POST":
        return JsonResponse({'data': 'Only POST allowed'}, status=405)

    try:
        service = MessagingService(provider=MessagingProvider.TWILIO)
        message = service.handle_inbound_message(request)
        return JsonResponse({'data': 'ok'}, status=200)
    except Exception as e:
        return JsonResponse({'data': f'Unexpected error: {str(e)}'}, status=500)