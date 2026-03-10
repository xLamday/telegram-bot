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
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
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

# Sessioni file-based — nessun DB Django necessario
SESSION_ENGINE       = "django.contrib.sessions.backends.file"
SESSION_FILE_PATH    = ROOT / ".sessions"
SESSION_COOKIE_AGE   = 60 * 60 * 8   # 8 ore
SESSION_COOKIE_HTTPONLY = True

# Nessun DB Django — usiamo SQLAlchemy tramite database/session.py
DATABASES = {}

STATIC_URL       = "/static/"
STATICFILES_DIRS = [ROOT / "web" / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# URL FastAPI per le chiamate interne Django → FastAPI
FASTAPI_URL = f"http://127.0.0.1:{web_config.FASTAPI_PORT}"
