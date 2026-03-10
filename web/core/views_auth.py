"""
web/core/views_auth.py — Login e logout del web panel.
Usa django.contrib.auth nativo + ottiene JWT da FastAPI al momento del login,
così le views possono chiamare le API protette senza ri-autenticarsi ogni volta.
"""
from __future__ import annotations

import requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods, require_GET
from django.contrib.auth import authenticate, login

from web.core.auth import (
    login_utente, logout_utente,
    get_current_user, seed_admin_if_missing,
)

# Stessa chiave usata in views.py
_JWT_SESSION_KEY = "_panel_jwt_access"
_JWT_REFRESH_KEY = "_panel_jwt_refresh"

API = settings.FASTAPI_URL


def _fetch_jwt(username: str, password: str) -> dict | None:
    """
    Chiama POST /api/auth/token su FastAPI e ritorna { access, refresh }.
    Se FastAPI non è raggiungibile ritorna None — il login Django è già avvenuto,
    le views gestiranno il 401 ricevendo None dai loro _get().
    """
    try:
        r = requests.post(
            f"{API}/api/auth/token",
            json={"username": username, "password": password},
            timeout=5,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


@require_http_methods(["GET", "POST"])
def login_view(request):

    if get_current_user(request):
        return redirect("dashboard")

    seed_admin_if_missing()

    error = None
    username = ""   # ✅ evita UnboundLocalError

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        from django.contrib.auth import authenticate, login

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_active:
            login(request, user)

            tokens = _fetch_jwt(username, password)
            if tokens:
                request.session[_JWT_SESSION_KEY] = tokens["access"]
                request.session[_JWT_REFRESH_KEY] = tokens["refresh"]

            return redirect("dashboard")

        error = "Credenziali non valide o account disabilitato."

    return render(
        request,
        "pages/login.html",
        {
            "error": error,
            "username": username,  # utile per ripopolare il form
        },
    )

@require_GET
def get_access_token(request):
    """
    Restituisce l'access token JWT salvato in sessione.
    """
    token = request.session.get(_JWT_SESSION_KEY, "")  # usa la tua chiave sessione
    return JsonResponse({"access": token})


def logout_view(request):
    # Rimuovi JWT dalla sessione prima di invalidarla
    request.session.pop(_JWT_SESSION_KEY, None)
    request.session.pop(_JWT_REFRESH_KEY, None)
    logout_utente(request)
    return redirect("login")
