import os

class EnvConfig:
    REQUIRED_VARS = [
        # Core / Security
        "DJANGO_SECRET",

        # Production
        "PRODUCTION",

        # Database
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "PGUSER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",

        # Server
        "SERVER_PORT",

        # Company
        "COMPANY_NAME",
        "SITE_NAME",
        "ROOT_DOMAIN",
        "DOMAIN_HOST",
        "COMPANY_PHONE_NUMBER",
        "COMPANY_EMAIL",

        # AWS
        "AWS_REGION",
        "AWS_STORAGE_BUCKET_NAME",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",

        # Facebook
        "FACEBOOK_ACCESS_TOKEN",
        "FACEBOOK_DATASET_ID",

        # Google Analytics & Ads
        "GOOGLE_ANALYTICS_API_KEY",
        "GOOGLE_ANALYTICS_ID",
        "GOOGLE_ADS_ID",
        "GOOGLE_ADS_CALL_CONVERSION_LABEL",
        "GOOGLE_REFRESH_TOKEN",

        # Twilio
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",

        # Stripe
        "STRIPE_API_KEY",
        "STRIPE_WEBHOOK_SECRET",

        # Facebook Leads Sheet
        "FACEBOOK_LEADS_SPREADSHEET_ID",
        "FACEBOOK_LEADS_SPREADSHEET_RANGE",

        # OpenAI
        "OPEN_AI_API_KEY",
    ]

    def __init__(self):
        missing = []

        self.DEFAULT_CURRENCY = 'USD'
        self.DEFAULT_LEAD_VALUE = '150.00'
        self.LEAD_EVENT_NAME = 'Lead'
        self.LEAD_GENERATED_EVENT_NAME = 'generate_lead'
        self.ASSUMED_BASE_HOURS = 4.00

        for var in self.REQUIRED_VARS:
            value = os.environ.get(var)
            setattr(self, var, value)
            if value is None:
                missing.append(var)

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

    def get(self, key: str, default=None):
        return getattr(self, key, default)