"""
Django views — recuperano dati dall'API FastAPI e li passano ai template.
"""
import requests
from django.conf import settings
from django.shortcuts import render

from web.core.auth import login_required, get_current_user

API = settings.FASTAPI_URL


def _get(endpoint: str):
    try:
        r = requests.get(f"{API}{endpoint}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _ctx(request, extra: dict) -> dict:
    """Aggiunge current_user al contesto di ogni template."""
    base = {"current_user": get_current_user(request)}
    base.update(extra)
    return base


@login_required
def dashboard(request):
    stats    = _get("/api/stats") or {}
    messaggi = _get("/api/messaggi?limit=10") or []
    logs     = _get("/api/logs?limit=5") or []
    return render(request, "pages/dashboard.html", _ctx(request, {
        "stats": stats, "messaggi": messaggi, "logs": logs, "page": "dashboard",
    }))


@login_required
def utenti(request):
    data = _get("/api/utenti") or []
    return render(request, "pages/utenti.html", _ctx(request, {"utenti": data, "page": "utenti"}))


@login_required
def canali(request):
    data = _get("/api/canali") or []
    return render(request, "pages/canali.html", _ctx(request, {"canali": data, "page": "canali"}))


@login_required
def messaggi(request):
    data = _get("/api/messaggi?limit=100") or []
    return render(request, "pages/messaggi.html", _ctx(request, {"messaggi": data, "page": "messaggi"}))


@login_required
def logs(request):
    data = _get("/api/logs?limit=200") or []
    return render(request, "pages/logs.html", _ctx(request, {"logs": data, "page": "logs"}))
