import json

from jotform import JotformAPIClient
from django.http import HttpResponse

from core.esign.base import ESignatureServiceInterface
from core.logger import logger
from core.email import email_service
from website import settings

class JotformSignService(ESignatureServiceInterface):
    def __init__(self):
        self.api_key = settings.JOTFORM_API_KEY
        self.client = JotformAPIClient(self.api_key)

    def get_forms(self):
        forms = self.client.get_forms()

        for form in forms:
            print(form["title"])
    
    def handle_esign_completed(self, request) -> HttpResponse:
        try:
            data = json.loads(request.body.decode("utf-8"))

            html = """
                <html>
                <body>
            """

            for key, value in data.items():
                html += f'<p><strong>{key}:</strong> {value}</p>'

            html += """
                </body>
                </html>
            """

            email_service.send_html_email(
                to=settings.COMPANY_EMAIL,
                subject='AGREEMENT SIGNED',
                html=html
            )

            return HttpResponse(status=200)

        except json.JSONDecodeError:
            return HttpResponse("Invalid JSON", status=400)
        except Exception as e:
            return HttpResponse(f"Error: {str(e)}", status=500)