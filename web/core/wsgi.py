"""
web/core/wsgi.py — WSGI application per Django.
"""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.core.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
