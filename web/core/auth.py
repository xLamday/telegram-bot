"""
web/core/auth.py

Autenticazione basata su:
  - django.contrib.auth  →  User nativo Django (hashing Argon2/PBKDF2 battle-tested)
  - djangorestframework-simplejwt  →  JWT per proteggere le API FastAPI
  - CsrfExempt solo sugli endpoint JWT (stateless per design)
  - login_required / admin_required usano il sistema di sessione Django nativo

Dipendenze da aggiungere a requirements.txt:
    djangorestframework
    djangorestframework-simplejwt
    django.contrib.auth (già incluso in Django)

INSTALLED_APPS richiesti:
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'rest_framework',
    'rest_framework_simplejwt',
"""
from __future__ import annotations

import os
from functools import wraps
from typing import Optional

from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponseForbidden
from django.shortcuts import redirect

# ── SimpleJWT ────────────────────────────────────────────────────────────────
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.authentication import JWTAuthentication


User = get_user_model()


# ── Token generation ──────────────────────────────────────────────────────────

def genera_token_per_utente(user: User) -> dict:
    """
    Restituisce access + refresh token JWT per un utente Django autenticato.
    Chiamato dopo login riuscito — il frontend salva i token e li include
    nell'header  Authorization: Bearer <access_token>  per ogni chiamata API.
    """
    refresh = RefreshToken.for_user(user)
    return {
        "access":  str(refresh.access_token),
        "refresh": str(refresh),
    }


def refresh_access_token(refresh_token_str: str) -> dict:
    """
    Dato un refresh token valido, restituisce un nuovo access token.
    Solleva InvalidToken / TokenError se scaduto o manomesso.
    """
    try:
        refresh = RefreshToken(refresh_token_str)
        return {"access": str(refresh.access_token)}
    except TokenError as e:
        raise InvalidToken(str(e))


# ── Verifica JWT per FastAPI ──────────────────────────────────────────────────
# FastAPI non usa Django middleware — questo helper verifica il token
# direttamente dal DB Django (stesso SECRET_KEY, stesso DB).

def verifica_jwt(token: str) -> Optional[User]:
    """
    Verifica un JWT Bearer e restituisce l'utente Django associato.
    Usato come dipendenza FastAPI per proteggere gli endpoint API.

    Esempio in app.py:
        from web.core.auth import verifica_jwt
        from fastapi import Header, HTTPException

        def jwt_required(authorization: str = Header(...)):
            token = authorization.removeprefix("Bearer ").strip()
            user = verifica_jwt(token)
            if not user:
                raise HTTPException(401, "Token non valido o scaduto")
            return user
    """
    try:
        jwt_auth = JWTAuthentication()
        # JWTAuthentication.get_validated_token valida firma + scadenza
        validated = jwt_auth.get_validated_token(
            jwt_auth.get_raw_token(
                jwt_auth.get_header(
                    type("FakeRequest", (), {
                        "META": {"HTTP_AUTHORIZATION": f"Bearer {token}"}
                    })()
                )
            )
        )
        return jwt_auth.get_user(validated)
    except Exception:
        return None


# ── Login / Logout Django session ─────────────────────────────────────────────

def login_utente(request: HttpRequest, username: str, password: str) -> Optional[User]:
    """
    Autentica con django.contrib.auth.authenticate (timing-safe, brute-force
    resistant grazie al rate limiting che puoi aggiungere con django-axes).
    Ritorna l'utente se le credenziali sono corrette, None altrimenti.
    """
    user = authenticate(request, username=username, password=password)
    if user is not None and user.is_active:
        login(request, user)          # ruota session ID → previene session fixation
        return user
    return None


def logout_utente(request: HttpRequest) -> None:
    logout(request)                   # invalida la sessione server-side


def get_current_user(request: HttpRequest) -> Optional[User]:
    """Utente corrente dalla sessione Django, o None se non autenticato."""
    if request.user.is_authenticated:
        return request.user
    return None


# ── Decoratori view Django ────────────────────────────────────────────────────

def login_required(view_func):
    """Redirect a 'login' se l'utente non è autenticato."""
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """403 se l'utente non è staff/superuser."""
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not (request.user.is_staff or request.user.is_superuser):
            return HttpResponseForbidden("Accesso riservato agli amministratori.")
        return view_func(request, *args, **kwargs)
    return wrapper


# ── Seed primo admin ──────────────────────────────────────────────────────────

def seed_admin_if_missing() -> None:
    """
    Crea il superuser iniziale se non ne esiste nessuno.
    Chiamato all'avvio di Django (AppConfig.ready) o da management command.
    Usa User.objects.create_superuser → hashing Argon2/PBKDF2 Django nativo.
    """
    admin_user = os.getenv("PANEL_ADMIN_USER", "admin")
    admin_pass = os.getenv("PANEL_ADMIN_PASS", "admin1234")

    if not User.objects.filter(is_superuser=True).exists():
        User.objects.create_superuser(
            username=admin_user,
            password=admin_pass,
            email="",
        )
        print(f"[AUTH] Superuser creato → {admin_user}")
        print("[AUTH] ⚠️  Cambia la password appena effettui il login!")
