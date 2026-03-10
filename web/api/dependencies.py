"""
web/api/dependencies.py
Verifica JWT tramite djangorestframework-simplejwt.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.core.settings")
try:
    django.setup()
except RuntimeError:
    pass  # già configurato

from fastapi import Header, HTTPException, status, Depends
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


def _get_user(authorization: str):
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header Authorization mancante o malformato.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    try:
        jwt_auth = JWTAuthentication()
        validated = jwt_auth.get_validated_token(token.encode())
        user = jwt_auth.get_user(validated)
        return user
    except (InvalidToken, TokenError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token non valido o scaduto: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def jwt_required(authorization: str = Header(...)):
    return _get_user(authorization)


def admin_required(user=Depends(jwt_required)):
    if not (user.is_staff or user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accesso riservato agli amministratori.",
        )
    return user
