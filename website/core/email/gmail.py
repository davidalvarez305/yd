import base64
from email.mime.text import MIMEText
from .base import EmailServiceInterface
from core.google.api import google_api_service

class GmailService(EmailServiceInterface):
    def __init__(self):
        """Inject a Gmail API client."""
        self.client = google_api_service

    def send_email(self, to: str, subject: str, body: str) -> None:
        """Send an email using Gmail API."""
        try:
            self.client.send_email(to=to, subject=subject, body=body)
        except Exception as e:
            raise Exception(f'Error sending e-mail.: {e}')
    
    def send_html_email(self, to: str, subject: str, html: str) -> None:
        """Send an email containing HTML using Gmail API."""
        try:
            self.client.send_html_email(to=to, subject=subject, html=html)
        except Exception as e:
            raise Exception(f'Error sending HTML e-mail.: {e}')