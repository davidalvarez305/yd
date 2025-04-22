from django.shortcuts import render
from core.enums import AlertStatus, AlertHTTPCodes

class AlertMixin:
    def alert(self, request, message, status: AlertStatus):
        template = 'core/success_alert.html' if status == AlertStatus.SUCCESS else 'core/error_alert.html'
        status_code = AlertHTTPCodes.get_http_code(status)
        return render(request, template_name=template, context={'message': message}, status=status_code)