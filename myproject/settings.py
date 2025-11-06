import os
from pathlib import Path
from datetime import timedelta
import environ
import dj_database_url

# ------------------------------
# Base directory
# ------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------
# Load environment variables
# ------------------------------
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["*"]),
    EMAIL_PORT=(int, 587),
    EMAIL_USE_TLS=(bool, True)
)

# Load .env file if exists
env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_file):
    print(f".env file found at {env_file}, loading it...")
    environ.Env.read_env(env_file)
else:
    print(".env file not found, using system environment variables")

# ------------------------------
# Core settings
# ------------------------------
SECRET_KEY = env("SECRET_KEY", default="unsafe-secret-key")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

# JWT secret (use for all JWT encode/decode)
JWT_SECRET = env("JWT_SECRET", default=SECRET_KEY)

# ------------------------------
# Installed apps
# ------------------------------
INSTALLED_APPS = [
    # Default
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Third-party
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    "rest_framework_simplejwt",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.apple",

    # Local apps
    "authentication",
    "payment",
    "tts_app",
    "bot",
    "dashboard",
]

SITE_ID = 1

# ------------------------------
# Middleware
# ------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",

]

# ------------------------------
# URLs & WSGI
# ------------------------------
ROOT_URLCONF = "myproject.urls"
WSGI_APPLICATION = "myproject.wsgi.application"
AUTH_USER_MODEL = "authentication.User"

# ------------------------------
# Templates
# ------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ------------------------------
# Database
# ------------------------------
DATABASES = {
    "default": dj_database_url.config(
        default=env("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
    )
}

# ------------------------------
# REST Framework
# ------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
}

# ------------------------------
# JWT Settings
# ------------------------------
SECRET_KEY = env("SECRET_KEY", default="unsafe-secret-key")
JWT_SECRET = env("JWT_SECRET", default=SECRET_KEY)
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "SIGNING_KEY": JWT_SECRET,  # Used for signing tokens
}

# ------------------------------
# Authentication Backends
# ------------------------------
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# ------------------------------
# Static & Media
# ------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ------------------------------
# Email
# ------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")

# ------------------------------
# CORS
# ------------------------------
CORS_ALLOW_ALL_ORIGINS = True

# ------------------------------
# Logging
# ------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "DEBUG"},
}

# ------------------------------
# API Keys
# ------------------------------
GOOGLE_API_KEY = env("GOOGLE_API_KEY", default=None)
OPENAI_API_KEY = env("OPENAI_API_KEY", default=None)

if not GOOGLE_API_KEY:
    print("⚠️ GOOGLE_API_KEY not configured in .env or system environment!")
else:
    print(f"✅ GOOGLE_API_KEY loaded successfully: {GOOGLE_API_KEY[:4]}...{GOOGLE_API_KEY[-4:]}")

# ------------------------------
# Google & Apple OAuth
# ------------------------------
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = env("GOOGLE_REDIRECT_URI")


APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID")
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID")
APPLE_KEY_ID = os.getenv("APPLE_KEY_ID")
APPLE_PRIVATE_KEY = os.getenv("APPLE_PRIVATE_KEY").replace("\\n", "\n")  # \n ঠিক করার জন্য
APPLE_BUNDLE_ID = os.getenv("APPLE_BUNDLE_ID")
redirect_uri = os.getenv("APPLE_CALLBACK_URL")

import jwt
import time

def generate_apple_client_secret():
    headers = {
        "kid": APPLE_KEY_ID,
        "alg": "ES256"
    }
    payload = {
        "iss": APPLE_TEAM_ID,
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400*180,  # 6 মাস বৈধ
        "aud": "https://appleid.apple.com",
        "sub": APPLE_CLIENT_ID,
    }
    client_secret = jwt.encode(payload, APPLE_PRIVATE_KEY, algorithm="ES256", headers=headers)
    return client_secret



SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': GOOGLE_CLIENT_ID,
            'secret': GOOGLE_CLIENT_SECRET,
            'key': ''
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    },
    'apple': {
        'APP': {
            'client_id': APPLE_CLIENT_ID,
            'secret': generate_apple_client_secret(),
            'key': APPLE_KEY_ID,
        },
        'SCOPE': ['name', 'email'],
        'AUTH_PARAMS': {
            'response_type': 'code id_token',
            'response_mode': 'form_post',
            'redirect_uri': redirect_uri
        }
    }
}


# ------------------------------
# Apple IAP & Google Service Account
# ------------------------------
APPLE_SHARED_SECRET = env("APPLE_SHARED_SECRET", default="")
GOOGLE_PACKAGE_NAME = env("GOOGLE_PACKAGE_NAME", default="")
GOOGLE_SERVICE_ACCOUNT_FILE = env("GOOGLE_SERVICE_ACCOUNT_FILE", default="")

from django.conf import settings
print("SECRET_KEY:", SECRET_KEY)
print("JWT_SECRET:", JWT_SECRET)

import os

APPLE_PRIVATE_KEY = os.getenv("APPLE_PRIVATE_KEY").replace("\\n", "\n")
