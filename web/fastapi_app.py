"""
web/fastapi_app.py
Entry point FastAPI — questo è il modulo che uvicorn carica come 'web.fastapi_app'.
Redirige semplicemente all'app definita in web/api/app.py.
"""
import sys
import os

# Assicura che la root del progetto sia nel sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from web.api.app import app  # noqa: F401 — uvicorn cercherà 'app' qui

__all__ = ["app"]
