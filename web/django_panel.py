"""
web/django_panel.py
Entry point Django — punta alle settings in web/core/settings.py.
Questo file esiste perché start_web.bat lo referenzia come modulo di settings.
"""
# Questo file non ha logica propria.
# Le Django settings sono in: web.core.settings
# Il WSGI app è in:           web.core.wsgi
#
# Viene importato solo per validare che il path sia corretto.

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.core.settings")
