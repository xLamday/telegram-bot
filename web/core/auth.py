"""
web/core/auth.py
Hashing password, decoratori sessione, seed admin.
Usa database/models.py e database/session.py del progetto reale.
"""
from __future__ import annotations

import hashlib
import os
import secrets
from functools import wraps
from typing import Optional

from django.http import HttpRequest
from django.shortcuts import redirect

from database.session import SyncSessionLocal
from database.models import PanelUser


# ── Hashing PBKDF2-SHA256 (zero dipendenze extra) ───────────────────────────

def _hash_password(password: str, salt: str | None = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return f"{salt}${dk.hex()}"


def verifica_password(password: str, stored_hash: str) -> bool:
    try:
        salt, _ = stored_hash.split("$", 1)
        return secrets.compare_digest(_hash_password(password, salt), stored_hash)
    except Exception:
        return False


def hash_password(password: str) -> str:
    return _hash_password(password)


# ── Session helpers ──────────────────────────────────────────────────────────

SESSION_KEY = "_panel_user_id"


def get_current_user(request: HttpRequest) -> Optional[PanelUser]:
    uid = request.session.get(SESSION_KEY)
    if not uid:
        return None
    db = SyncSessionLocal()
    try:
        u = db.query(PanelUser).filter_by(id=uid).first()
        # Detach per usarlo fuori dalla sessione
        if u:
            db.expunge(u)
        return u
    finally:
        db.close()


def login_user(request: HttpRequest, user: PanelUser) -> None:
    request.session[SESSION_KEY] = user.id
    request.session.set_expiry(60 * 60 * 8)


def logout_user(request: HttpRequest) -> None:
    request.session.flush()


# ── Decoratori ───────────────────────────────────────────────────────────────

def login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get(SESSION_KEY):
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        uid = request.session.get(SESSION_KEY)
        if not uid:
            return redirect("login")
        db = SyncSessionLocal()
        try:
            u = db.query(PanelUser).filter_by(id=uid).first()
        finally:
            db.close()
        if not u or u.ruolo != "admin":
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Accesso riservato agli admin.")
        return view_func(request, *args, **kwargs)
    return wrapper


# ── Seed primo admin ─────────────────────────────────────────────────────────

def seed_admin_if_missing() -> None:
    admin_user = os.getenv("PANEL_ADMIN_USER", "admin")
    admin_pass = os.getenv("PANEL_ADMIN_PASS", "admin1234")
    db = SyncSessionLocal()
    try:
        if db.query(PanelUser).filter_by(ruolo="admin").count() == 0:
            db.add(PanelUser(
                username=admin_user,
                password_hash=hash_password(admin_pass),
                nome="Amministratore",
                ruolo="admin",
            ))
            db.commit()
            print(f"[AUTH] Admin creato → {admin_user} / {admin_pass}")
            print("[AUTH] ⚠️  Cambia la password appena effettui il login!")
    except Exception:
        db.rollback()
    finally:
        db.close()
