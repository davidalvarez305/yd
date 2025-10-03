import json

from jotform import JotformAPIClient
from django.http import HttpResponse

from core.esign.base import ESignatureServiceInterface
from core.logger import logger
from website import settings

class JotformSignService(ESignatureServiceInterface):
    def __init__(self):
        self.api_key = settings.JOTFORM_API_KEY
        self.client = JotformAPIClient(self.api_key)

    def get_forms(self):
        forms = self.client.get_forms()

        for form in forms:
            print(form["title"])
    
    def handle_agreement_signed(self, request) -> HttpResponse:
        try:
            data = json.loads(request.body.decode("utf-8"))

            print(data)
            return HttpResponse(status=200)

        except Exception as e:
            logger.error(f"Error handling Jotform Agreement Signed webhook {e}", exc_info=True)
            return HttpResponse("An unexpected error occurred.", status=500)