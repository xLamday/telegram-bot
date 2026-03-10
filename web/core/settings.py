"""
web/core/settings.py
Django settings — usa shared/config.py come unica sorgente di config.
"""
import sys
import os
from pathlib import Path

# Root del progetto nel sys.path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Importa config condivisa (carica anche il .env)
from shared.config import web_config, db_config

BASE_DIR = Path(__file__).resolve().parent.parent   # = cartella web/

SECRET_KEY    = web_config.SECRET_KEY
DEBUG         = web_config.DEBUG
ALLOWED_HOSTS = web_config.ALLOWED_HOSTS or ["*"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.sessions",
    "web.core",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    'rest_framework',
    'rest_framework_simplejwt',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "web.core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [ROOT / "web" / "templates"],
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
            ],
            "loaders": [
                "django.template.loaders.filesystem.Loader",
            ],
        },
    },
]

WSGI_APPLICATION = "web.core.wsgi.application"

# Sessioni DB-backed — richiesto da django.contrib.auth
SESSION_ENGINE          = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE      = 60 * 60 * 8   # 8 ore
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE   = False          # True in produzione con HTTPS

# DB Django — solo per auth, sessioni e admin. Il bot usa SQLAlchemy separato.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_panel.sqlite3",
    }
}

# Password validators Django
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# SimpleJWT config
from datetime import timedelta
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS":  True,
    "ALGORITHM":              "HS256",
    "SIGNING_KEY":            SECRET_KEY,
}

# DRF — usa JWT come autenticazione di default
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

STATIC_URL       = "/static/"
STATICFILES_DIRS = [ROOT / "web" / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# URL FastAPI per le chiamate interne Django → FastAPI
FASTAPI_URL = f"http://127.0.0.1:{web_config.FASTAPI_PORT}"
