import base64
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText

from website import settings

class EmailService:
    def __init__(self, client):
        self.client = client

    def send_email(self, to: str, subject: str, body: str) -> None:
        """Method to send an email. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement send_email method")

class GmailService:
    def __init__(self, client):
        """Inject a Gmail API client."""
        self.client = client

    def send_email(self, to: str, subject: str, body: str) -> None:
        """Send an email using Gmail API."""
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        self.client.users().messages().send(userId="me", body={"raw": raw_message}).execute()


def initialize_gmail_client():
    """Authenticate and return a Gmail API client."""
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", settings.GOOGLE_API_SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", settings.GOOGLE_API_SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

def get_email_service() -> EmailService:
    """Return the configured email service (e.g., Gmail, SendGrid, etc.).
    Swap this with another provider if needed
    """
    client = initialize_gmail_client()
    return GmailService(client=client) 