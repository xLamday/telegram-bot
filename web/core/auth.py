"""
web/core/auth.py
Autenticazione tramite django.contrib.auth (tabella auth_user).
JWT tramite djangorestframework-simplejwt.
"""
from __future__ import annotations

import os
from functools import wraps
from typing import Optional

from django.contrib.auth import authenticate, login, logout, get_user_model
from django.http import HttpRequest, HttpResponseForbidden
from django.shortcuts import redirect

User = get_user_model()


def _ruolo(user) -> str:
    return "admin" if (user.is_superuser or user.is_staff) else "viewer"


def get_current_user(request: HttpRequest):
    """Ritorna il Django User con .ruolo iniettato, o None."""
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return None
    user = request.user
    user.ruolo = _ruolo(user)
    return user


def login_utente(request: HttpRequest, username: str, password: str):
    user = authenticate(request, username=username, password=password)
    if user is not None and user.is_active:
        login(request, user)
        return user
    return None


def logout_utente(request: HttpRequest) -> None:
    logout(request)


# ── Decoratori ────────────────────────────────────────────────────────────────

def login_required(view_func):
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not (request.user.is_staff or request.user.is_superuser):
            return HttpResponseForbidden("Accesso riservato agli amministratori.")
        return view_func(request, *args, **kwargs)
    return wrapper


# ── Seed ──────────────────────────────────────────────────────────────────────

def seed_admin_if_missing() -> None:
    admin_user = os.getenv("PANEL_ADMIN_USER", "admin")
    admin_pass = os.getenv("PANEL_ADMIN_PASS", "admin1234")
    if not User.objects.filter(is_superuser=True).exists():
        User.objects.create_superuser(username=admin_user, password=admin_pass, email="")
        print(f"[AUTH] Superuser creato → {admin_user}")


# ── JWT via simplejwt ─────────────────────────────────────────────────────────

def genera_token_per_utente(user) -> dict:
    """Genera access + refresh token tramite simplejwt."""
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    # Aggiungi ruolo nel payload del token
    refresh["role"] = _ruolo(user)
    refresh.access_token["role"] = _ruolo(user)
    return {
        "access":  str(refresh.access_token),
        "refresh": str(refresh),
    }


def verifica_jwt(token: str) -> Optional[User]:
    """Verifica un access token JWT e ritorna l'utente. Usato da FastAPI."""
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
    try:
        jwt_auth = JWTAuthentication()
        validated = jwt_auth.get_validated_token(token.encode())
        return jwt_auth.get_user(validated)
    except (InvalidToken, TokenError):
        return None


def refresh_access_token(refresh_token_str: str) -> dict:
    """Rinnova l'access token dato un refresh token valido."""
    from rest_framework_simplejwt.tokens import RefreshToken
    from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
    try:
        refresh = RefreshToken(refresh_token_str)
        return {"access": str(refresh.access_token)}
    except TokenError as e:
        raise InvalidToken(str(e))
