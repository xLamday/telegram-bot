"""
web/api/dependencies.py

Dipendenze FastAPI per autenticazione JWT.
Ogni endpoint protetto aggiunge:

    from web.api.dependencies import jwt_required, admin_required
    
    @app.get("/api/canali")
    def get_canali(user = Depends(jwt_required)):
        ...

    @app.delete("/api/canali/{id}")
    def rimuovi(id: int, user = Depends(admin_required)):
        ...

Il frontend deve includere in ogni chiamata:
    Authorization: Bearer <access_token>
"""
from __future__ import annotations

import os
import django

# Assicura che Django sia configurato prima di usare i suoi moduli
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.core.settings")
try:
    django.setup()
except RuntimeError:
    pass  # già configurato

from fastapi import Depends, Header, HTTPException, status
from web.core.auth import verifica_jwt


# ── Dependency base ───────────────────────────────────────────────────────────

def jwt_required(authorization: str = Header(..., description="Bearer <access_token>")):
    """
    Verifica il JWT nell'header Authorization.
    Ritorna l'utente Django se valido, altrimenti 401.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header Authorization mancante o malformato. Formato: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    user = verifica_jwt(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token non valido o scaduto. Esegui nuovamente il login.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def admin_required(user=Depends(jwt_required)):
    """
    Estende jwt_required — verifica anche che l'utente sia staff o superuser.
    Ritorna 403 altrimenti.
    """
    if not (user.is_staff or user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accesso riservato agli amministratori.",
        )
    return user
