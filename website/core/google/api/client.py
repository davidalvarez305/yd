import base64
import json
import os
from email.mime.text import MIMEText

from django.conf import settings

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from core.models import GoogleAccessToken
from core.logger import logger

CREDENTIALS_PATH = os.path.join(settings.PROJECT_ROOT, 'credentials.json')

class GoogleAPIService:
    def __init__(self):
        self.token = GoogleAccessToken.objects.order_by("-date_created").first()
        if not self.token:
            raise Exception("No Google access token found in DB.")

        self.creds = self._load_credentials()
        self.location_id = settings.GOOGLE_BUSINESS_PROFILE_LOCATION_ID
        self.account_id = settings.GOOGLE_BUSINESS_PROFILE_ACCOUNT_ID

        self.gmail = self.build("gmail", "v1")
        self.sheets = self.build("sheets", "v4")
        self.mybusiness = self.build("mybusiness", "v4")

    def _load_credentials(self) -> Credentials:
        try:
            with open(CREDENTIALS_PATH, "r") as f:
                credentials_data = json.load(f)

            client_info = credentials_data.get("installed") or credentials_data.get("web")
            client_id = client_info["client_id"]
            client_secret = client_info["client_secret"]

            creds = Credentials(
                token=self.token.access_token,
                refresh_token=self.token.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=settings.GOOGLE_API_SCOPES,
            )

            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                self.token.access_token = creds.token
                self.token.date_expires = creds.expiry
                self.token.save()

            return creds

        except Exception as e:
            logger.error("Failed to load Google credentials", exc_info=True)
            raise

    def build(self, api_name: str, api_version: str):
        return build(api_name, api_version, credentials=self.creds)

    def send_email(self, to: str, subject: str, body: str) -> None:
        try:
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

            self.gmail.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()
        except Exception as e:
            logger.error("Failed to send email via Gmail API", exc_info=True)
            raise

    def get_sheet_data(self, spreadsheet_id: str, range_name: str) -> list[dict]:
        try:
            sheet = self.sheets.spreadsheets().values()
            result = sheet.get(spreadsheetId=spreadsheet_id, range=range_name).execute()
            values = result.get("values", [])
            headers = values[0] if values else []
            return [dict(zip(headers, row)) for row in values[1:]]
        except Exception as e:
            logger.error("Failed to fetch Google Sheet data", exc_info=True)
            raise

    def append_sheet_data(self, spreadsheet_id: str, range_name: str, data: list[dict]) -> dict:
        try:
            if not data:
                return {}

            headers = list(data[0].keys())
            rows = [[str(row.get(h, "")) for h in headers] for row in data]
            body = {"values": [headers] + rows}

            return self.sheets.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body
            ).execute()
        except Exception as e:
            logger.error("Failed to append to Google Sheet", exc_info=True)
            raise

    def sync_reviews(self) -> list[dict]:
        try:
            response = self.mybusiness.accounts().locations().reviews().list(
                parent=f"locations/{self.location_id}"
            ).execute()
            return response.get("reviews", [])
        except Exception as e:
            logger.error("Failed to sync Google Reviews", exc_info=True)
            raise