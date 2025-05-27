from django.shortcuts import render
from core.enums import AlertStatus, AlertHTTPCodes

class AlertMixin:
    def alert(self, request, message, status: AlertStatus, reswap = False):
        template = 'core/success_alert.html' if status == AlertStatus.SUCCESS else 'core/error_alert.html'
        status_code = AlertHTTPCodes.get_http_code(status)

        response = render(request, template_name=template, context={'message': message}, status=status_code)
        if reswap:
            response['HX-Reswap'] = 'outerHTML'
            response['HX-Retarget'] = '#alertModal'
        return response