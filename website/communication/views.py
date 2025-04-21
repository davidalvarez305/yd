from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpRequest

from .messaging import MessagingService
from .enums import MessagingProvider

@csrf_exempt
def handle_inbound_message(request: HttpRequest):
    if request.method != "POST":
        return JsonResponse({'data': 'Only POST allowed'}, status=405)

    try:
        service = MessagingService(provider=MessagingProvider.TWILIO)
        service.handle_inbound_message(request)
        return JsonResponse({'data': 'ok'}, status=200)
    except Exception as e:
        return JsonResponse({'data': f'Unexpected error: {str(e)}'}, status=500)

@csrf_exempt
def handle_outbound_message(request: HttpRequest):
    if request.method != "POST":
        return JsonResponse({'data': 'Only POST allowed'}, status=405)

    try:
        service = MessagingService(provider=MessagingProvider.TWILIO)
        service.handle_outbound_message(request)
        return JsonResponse({'data': 'ok'}, status=200)
    except Exception as e:
        return JsonResponse({'data': f'Unexpected error: {str(e)}'}, status=500)