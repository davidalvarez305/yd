import os
from pathlib import Path
from dotenv import load_dotenv
from .env import EnvConfig

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()
env = EnvConfig()

SECRET_KEY = env.get("DJANGO_SECRET")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.get("PRODUCTION") == "0"

ALLOWED_HOSTS = env.get("ALLOWED_HOSTS", "127.0.0.1").split(',')
LOGIN_URL = "/login"  # Change this to your desired login URL

# Application definition
INSTALLED_APPS = [
    'crm',
    'core.apps.CoreConfig',
    'communication',
    'marketing',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
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


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
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

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# AWS
AWS_ACCESS_KEY_ID = env.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env.get("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = env.get("AWS_STORAGE_BUCKET_NAME")
AWS_S3_CUSTOM_DOMAIN = env.get("AWS_S3_CUSTOM_DOMAIN")
AWS_S3_REGION_NAME = env.get('AWS_REGION')

# AWS Custom Config
AWS_QUERYSTRING_AUTH = False
AWS_IS_GZIPPED = True # text/css,text/javascript,application/javascript,application/x-javascript,image/svg+xml
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",  # Cache files for 24 hours
}

# Env
PRODUCTION = env.get("PRODUCTION")
POSTGRES_HOST = env.get("POSTGRES_HOST")
POSTGRES_PORT = env.get("POSTGRES_PORT")
PGUSER = env.get("PGUSER")
POSTGRES_PASSWORD = env.get("POSTGRES_PASSWORD")
POSTGRES_DB = env.get("POSTGRES_DB")
SERVER_PORT = env.get("SERVER_PORT")

COMPANY_NAME = env.get("COMPANY_NAME")
SITE_NAME = env.get("SITE_NAME")
COMPANY_PHONE_NUMBER = env.get("COMPANY_PHONE_NUMBER")
COMPANY_EMAIL = env.get("COMPANY_EMAIL")
ROOT_DOMAIN = env.get("ROOT_DOMAIN")
DOMAIN_HOST = env.get("DOMAIN_HOST")

GOOGLE_ANALYTICS_API_KEY = env.get("GOOGLE_ANALYTICS_API_KEY")
GOOGLE_ANALYTICS_ID = env.get("GOOGLE_ANALYTICS_ID")
GOOGLE_ADS_ID = env.get("GOOGLE_ADS_ID")
GOOGLE_ADS_CALL_CONVERSION_LABEL = env.get("GOOGLE_ADS_CALL_CONVERSION_LABEL")
GOOGLE_REFRESH_TOKEN = env.get("GOOGLE_REFRESH_TOKEN")

FACEBOOK_ACCESS_TOKEN = env.get("FACEBOOK_ACCESS_TOKEN")
FACEBOOK_DATASET_ID = env.get("FACEBOOK_DATASET_ID")

TWILIO_ACCOUNT_SID = env.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = env.get("TWILIO_AUTH_TOKEN")

STRIPE_API_KEY = env.get("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = env.get("STRIPE_WEBHOOK_SECRET")

FACEBOOK_LEADS_SPREADSHEET_ID = env.get("FACEBOOK_LEADS_SPREADSHEET_ID")
FACEBOOK_LEADS_SPREADSHEET_RANGE = env.get("FACEBOOK_LEADS_SPREADSHEET_RANGE")

OPEN_AI_API_KEY = env.get("OPEN_AI_API_KEY")

LEAD_EVENT_NAME = env.get("LEAD_EVENT_NAME")
LEAD_GENERATED_EVENT_NAME = env.get("LEAD_GENERATED_EVENT_NAME")
DEFAULT_CURRENCY = env.get("DEFAULT_CURRENCY")
DEFAULT_LEAD_VALUE = env.get("DEFAULT_LEAD_VALUE")
ASSUMED_BASE_HOURS = env.get("ASSUMED_BASE_HOURS")

# Files
if DEBUG is not True:
    STATIC_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/static/"
else:
    STATIC_URL = "/static/"
    STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
    STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/media/"

# Storage Configuration
if DEBUG:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
        "media": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "location": "media",
            },
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
            },
        },
        "staticfiles": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
            },
        },
        "media": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "location": "media",
            },
        },
    }

# Ensure media is always stored on S3
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

# Google API
GOOGLE_API_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets"
]

# User
AUTH_USER_MODEL = 'core.User'