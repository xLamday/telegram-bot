"""
web/core/views.py
Django views — recuperano dati dall'API FastAPI con JWT nell'header.
Il token viene ottenuto dalla sessione Django (salvato al login).
"""
from __future__ import annotations

import requests
from django.conf import settings
from django.shortcuts import render

from web.core.auth import login_required, get_current_user

API = settings.FASTAPI_URL

# Chiave sessione dove salviamo l'access token JWT dopo il login
_JWT_SESSION_KEY = "_panel_jwt_access"


def _auth_headers(request) -> dict:
    """
    Ritorna l'header Authorization con il JWT salvato in sessione.
    Se il token è assente (non dovrebbe accadere dopo login_required)
    ritorna un dict vuoto — FastAPI risponderà 401.
    """
    token = request.session.get(_JWT_SESSION_KEY, "")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _get(endpoint: str, request) -> dict | list | None:
    """GET autenticato verso FastAPI."""
    try:
        r = requests.get(
            f"{API}{endpoint}",
            headers=_auth_headers(request),
            timeout=5,
        )
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        # 401 → token scaduto, forza il re-login al prossimo ciclo
        if e.response is not None and e.response.status_code == 401:
            request.session.pop(_JWT_SESSION_KEY, None)
        return None
    except Exception:
        return None


def _post(endpoint: str, request, json: dict) -> dict | None:
    """POST autenticato verso FastAPI."""
    try:
        r = requests.post(
            f"{API}{endpoint}",
            headers=_auth_headers(request),
            json=json,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            request.session.pop(_JWT_SESSION_KEY, None)
        return None
    except Exception:
        return None


def _ctx(request, extra: dict) -> dict:
    """Aggiunge current_user al contesto di ogni template."""
    base = {"current_user": get_current_user(request)}
    base.update(extra)
    return base


# ── Views protette ────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    stats    = _get("/api/stats",         request) or {}
    messaggi = _get("/api/messaggi?limit=10", request) or []
    logs     = _get("/api/logs?limit=5",  request) or []
    return render(request, "pages/dashboard.html", _ctx(request, {
        "stats": stats, "messaggi": messaggi, "logs": logs, "page": "dashboard",
    }))


@login_required
def utenti(request):
    data = _get("/api/utenti", request) or []
    return render(request, "pages/utenti.html", _ctx(request, {
        "utenti": data, "page": "utenti",
    }))


@login_required
def canali(request):
    data = _get("/api/canali", request) or []
    return render(request, "pages/canali.html", _ctx(request, {
        "canali": data, "page": "canali",
    }))


@login_required
def messaggi(request):
    data = _get("/api/messaggi?limit=100", request) or []
    return render(request, "pages/messaggi.html", _ctx(request, {
        "messaggi": data, "page": "messaggi",
    }))


@login_required
def logs(request):
    data = _get("/api/logs?limit=200", request) or []
    return render(request, "pages/logs.html", _ctx(request, {
        "logs": data, "page": "logs",
    }))
