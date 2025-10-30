import os
from pathlib import Path
from dotenv import load_dotenv
from .env import EnvConfig


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = os.path.dirname(BASE_DIR)

load_dotenv()
env = EnvConfig()

SECRET_KEY = env.get("DJANGO_SECRET")

DEBUG = env.get("PRODUCTION") == "0"

ALLOWED_HOSTS = [env.get('ALLOWED_HOSTS'), env.get('NGROK_HOST')]
LOGIN_URL = "/login"

# Application definition
INSTALLED_APPS = [
    'crm.apps.CrmConfig',
    'core.apps.CoreConfig',
    'marketing.apps.MarketingConfig',
    'communication',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'website.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'website.wsgi.application'

# Cors
CORS_ALLOWED_ORIGINS = [env.get('ROOT_DOMAIN')]
CORS_ALLOW_CREDENTIALS = True

# Database
POSTGRES_HOST = env.get("POSTGRES_HOST")
POSTGRES_PORT = env.get("POSTGRES_PORT")
PGUSER = env.get("PGUSER")
POSTGRES_PASSWORD = env.get("POSTGRES_PASSWORD")
POSTGRES_DB = env.get("POSTGRES_DB")

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': POSTGRES_DB,
        'USER': PGUSER,
        'PASSWORD': POSTGRES_PASSWORD,
        'HOST': POSTGRES_HOST,
        'PORT': POSTGRES_PORT,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/New_York'

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# AWS
AWS_ACCESS_KEY_ID = env.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env.get("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = env.get("AWS_STORAGE_BUCKET_NAME")
AWS_S3_CUSTOM_DOMAIN = env.get("AWS_S3_CUSTOM_DOMAIN")
AWS_S3_REGION_NAME = env.get('AWS_REGION')
AWS_CLOUDFRONT_DISTRIBUTION_ID = env.get('AWS_CLOUDFRONT_DISTRIBUTION_ID')
AWS_QUERYSTRING_AUTH = False
AWS_IS_GZIPPED = True
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",  # Cache files for 24 hours
}

# Env
PRODUCTION = env.get("PRODUCTION")

COMPANY_NAME = env.get("COMPANY_NAME")
SITE_NAME = env.get("SITE_NAME")
COMPANY_PHONE_NUMBER = env.get("COMPANY_PHONE_NUMBER")
COMPANY_EMAIL = env.get("COMPANY_EMAIL")
ROOT_DOMAIN = env.get("ROOT_DOMAIN")
DOMAIN_HOST = env.get("DOMAIN_HOST")
NGROK_HOST = env.get("NGROK_HOST")

GOOGLE_API_CREDENTIALS_PATH = os.path.join(PROJECT_ROOT, 'credentials.json')
GOOGLE_ANALYTICS_API_KEY = env.get("GOOGLE_ANALYTICS_API_KEY")
GOOGLE_ANALYTICS_ID = env.get("GOOGLE_ANALYTICS_ID")
GOOGLE_REFRESH_TOKEN = env.get("GOOGLE_REFRESH_TOKEN")
GOOGLE_BUSINESS_PROFILE_ACCOUNT_ID = env.get('GOOGLE_BUSINESS_PROFILE_ACCOUNT_ID')
GOOGLE_BUSINESS_PROFILE_LOCATION_ID = env.get('GOOGLE_BUSINESS_PROFILE_LOCATION_ID')
GOOGLE_ADS_CALL_CONVERSION_LABEL = env.get('GOOGLE_ADS_CALL_CONVERSION_LABEL')
GOOGLE_ADS_DEVELOPER_TOKEN = env.get('GOOGLE_ADS_DEVELOPER_TOKEN')
GOOGLE_ADS_ID = env.get('GOOGLE_ADS_ID')
GOOGLE_ADS_CUSTOMER_ID = env.get('GOOGLE_ADS_CUSTOMER_ID')

EVENT_BOOKED_GOOGLE_ADS_CONVERSION_ACTION_ID = 7355438593

FACEBOOK_API_VERSION = env.get("FACEBOOK_API_VERSION")
FACEBOOK_PAGE_ACCESS_TOKEN = env.get("FACEBOOK_PAGE_ACCESS_TOKEN")
FACEBOOK_CAPI_ACCESS_TOKEN = env.get("FACEBOOK_CAPI_ACCESS_TOKEN")
FACEBOOK_DATASET_ID = env.get("FACEBOOK_DATASET_ID")
FACEBOOK_APP_ID = env.get("FACEBOOK_APP_ID")
FACEBOOK_APP_VERIFY_TOKEN = env.get("FACEBOOK_APP_VERIFY_TOKEN")
FACEBOOK_APP_SECRET = env.get("FACEBOOK_APP_SECRET")
FACEBOOK_APP_CLIENT_TOKEN = env.get("FACEBOOK_APP_CLIENT_TOKEN")
FACEBOOK_PAGE_ID = env.get("FACEBOOK_PAGE_ID")
FACEBOOK_LEADS_SPREADSHEET_ID = env.get("FACEBOOK_LEADS_SPREADSHEET_ID")
FACEBOOK_LEADS_SPREADSHEET_RANGE = env.get("FACEBOOK_LEADS_SPREADSHEET_RANGE")
FACEBOOK_AD_ACCOUNT_ID = env.get("FACEBOOK_AD_ACCOUNT_ID")

TWILIO_ACCOUNT_SID = env.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = env.get("TWILIO_AUTH_TOKEN")

STRIPE_API_KEY = env.get("STRIPE_API_KEY")
STRIPE_TEST_API_KEY = env.get("STRIPE_TEST_API_KEY")
STRIPE_TEST_WEBHOOK_SECRET = env.get("STRIPE_TEST_WEBHOOK_SECRET")
STRIPE_WEBHOOK_SECRET = env.get("STRIPE_WEBHOOK_SECRET")

CALL_RAIL_API_KEY = env.get("CALL_RAIL_API_KEY")
CALL_RAIL_ACCOUNT_ID = env.get("CALL_RAIL_ACCOUNT_ID")

OPEN_AI_API_KEY = env.get("OPEN_AI_API_KEY")

LEAD_EVENT_NAME = env.get("LEAD_EVENT_NAME")
LEAD_GENERATED_EVENT_NAME = env.get("LEAD_GENERATED_EVENT_NAME")
DEFAULT_CURRENCY = env.get("DEFAULT_CURRENCY")
DEFAULT_LEAD_VALUE = env.get("DEFAULT_LEAD_VALUE")
ASSUMED_BASE_HOURS = env.get("ASSUMED_BASE_HOURS")

GOOGLE_ADS_CALL_ASSET_PHONE_NUMBER = env.get("GOOGLE_ADS_CALL_ASSET_PHONE_NUMBER")

ARCHIVED_LEAD_STATUS_ID = 7
NO_INTEREST_LEAD_INTEREST_ID = 4

# Files
# STATIC_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/static/"
if DEBUG is not True:
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
else:
    STATIC_URL = "/static/"
    STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
    STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/media/"
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
UPLOADS_URL = os.path.join(BASE_DIR, "uploads")

# Storage Configuration
if DEBUG:
    STORAGES = {
        "default": {
            "BACKEND": "core.storage.MediaS3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
        "media": {
            "BACKEND": "core.storage.MediaS3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "location": "media",
            },
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "core.storage.MediaS3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
            },
        },
        "staticfiles": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "location": "static",
            },
        },
        "media": {
            "BACKEND": "core.storage.MediaS3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "location": "media",
            },
        },
    }

# Ensure media is always stored on S3
DEFAULT_FILE_STORAGE = "core.storage.MediaS3Storage"

# Google API
GOOGLE_API_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/adwords",
    # "https://www.googleapis.com/auth/business.manage"
]

# User
AUTH_USER_MODEL = 'core.User'

# Communication Services
MESSAGING_SERVICE = 'core.messaging.twilio.TwilioMessagingService'
CALLING_SERVICE = 'core.calling.twilio.TwilioCallingService'
AI_AGENT_SERVICE = 'core.ai.openai.OpenAIAgentService'
EMAIL_SERVICE = 'core.email.gmail.GmailService'
FACEBOOK_API_SERVICE = 'core.facebook.api.client.FacebookAPIService'
BILLING_SERVICE = 'core.billing.stripe.StripeBillingService'
REVIEWS_SERVICE = 'core.reviews.google.GoogleReviewsService'
GOOGLE_API_SERVICE = 'core.google.api.client.GoogleAPIService'
CALL_TRACKING_SERVICE = 'core.call_tracking.callrail.CallRailTrackingService'

TRANSCRIPTION_SERVICE = 'core.transcription.aws.AWSTranscriptionService'
TRANSCRIPTION_STORAGE_PREFIX = 'uploads/jobs/'

# Marketing Services
CONVERSION_SERVICES = {
    "google": {
        "BACKEND": "core.conversions.google.GoogleAnalyticsConversionService",
        "OPTIONS": {
            "google_analytics_id": GOOGLE_ANALYTICS_ID,
            "google_analytics_api_key": GOOGLE_ANALYTICS_API_KEY,
        },
    },
    "facebook": {
        "BACKEND": "core.conversions.facebook.FacebookConversionService",
        "OPTIONS": {
            "pixel_id": FACEBOOK_DATASET_ID,
            "access_token": FACEBOOK_CAPI_ACCESS_TOKEN,
            "version": FACEBOOK_API_VERSION,
        },
    },
    "gads": {
        "BACKEND": "core.conversions.gads.GoogleAdsConversionService",
        "OPTIONS": {
            'developer_token': GOOGLE_ADS_DEVELOPER_TOKEN,
            'customer_id': GOOGLE_ADS_CUSTOMER_ID,
            'conversion_actions': {
                'event_booked': EVENT_BOOKED_GOOGLE_ADS_CONVERSION_ACTION_ID,
            }
        },
    },
}

CALL_TRACKING_EXPIRATION_LIMIT = 10.00

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'handlers': {
        'db': {
            'level': 'ERROR',
            'class': 'core.logs.handler.DatabaseLogHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },

    'loggers': {
        'django': {
            'handlers': ['console', 'db'],
            'level': 'INFO',
            'propagate': True,
        },
        'internal': {
            'handlers': ['console', 'db'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}

# Max memory before files are streamed to disk (default is 2.5MB)
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 50  # 50 MB

# Max size Django will accept for request body (POST, file uploads, etc.)
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 50  # 50 MB

# Max header sizes
DATA_UPLOAD_MAX_HEADER_SIZE = 1024 * 1024 * 50 # 50 MB
MAX_TOTAL_HEADER_SIZE = 1024 * 1024 * 50 # 50 MB

DEFAULT_TRACKING_NUMBER = env.get('GOOGLE_ADS_CALL_ASSET_PHONE_NUMBER')

TRACKING_COOKIE_NAME = '_yd'