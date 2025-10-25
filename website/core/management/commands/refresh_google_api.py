import json
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import make_aware, is_naive
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from core.models import GoogleAccessToken
from django.conf import settings

class Command(BaseCommand):
    help = "Refresh or reauthorize Google OAuth credentials if scopes changed or token expired."

    def handle(self, *args, **options):
        try:
            with open(settings.GOOGLE_API_CREDENTIALS_PATH, "r") as f:
                credentials_data = json.load(f)

            client_info = credentials_data.get("installed") or credentials_data.get("web")
            client_id = client_info["client_id"]
            client_secret = client_info["client_secret"]

            required_scopes = set(settings.GOOGLE_API_SCOPES)
            token = GoogleAccessToken.objects.order_by("-date_created").first()

            if not token:
                creds = self._authorize_new(credentials_data, required_scopes)
                self._save_token(creds)
                return

            stored_scopes = set((token.scope or "").split(","))

            if stored_scopes != required_scopes:
                creds = self._authorize_new(credentials_data, required_scopes)
                self._save_token(creds)
                return

            creds = Credentials(
                token=token.access_token,
                refresh_token=token.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=list(required_scopes),
            )

            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                self._save_token(creds)

        except Exception as e:
            raise CommandError(f"❌ Failed to refresh Google credentials: {e}")

    def _authorize_new(self, credentials_data, scopes):
        flow = Flow.from_client_config(credentials_data, scopes=list(scopes))
        flow.redirect_uri = "http://127.0.0.1:8000"

        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

        print("\n🔗 Open this link in your browser to authorize:")
        print(auth_url)

        code = input("Enter the authorization code: ")

        flow.fetch_token(code=code)
        return flow.credentials

    def _save_token(self, creds):
        date_expires = creds.expiry
        if is_naive(date_expires):
            date_expires = make_aware(date_expires)

        GoogleAccessToken.objects.create(
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            scope=",".join(creds.scopes),
            date_expires=date_expires,
        )