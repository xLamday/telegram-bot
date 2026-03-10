"""
web/core/views_admin_panel.py — Gestione utenti del web panel (solo admin).
"""
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods, require_POST

from database.session import SyncSessionLocal
from database.models import PanelUser
from web.core.auth import (
    admin_required, login_required,
    hash_password, verifica_password, get_current_user,
)
from datetime import datetime


def _lista_utenti_panel():
    db = SyncSessionLocal()
    try:
        return [
            {
                "id":           u.id,
                "username":     u.username,
                "nome":         u.nome,
                "ruolo":        u.ruolo,
                "attivo":       u.attivo,
                "creato_il":    str(u.creato_il)[:16],
                "ultimo_login": str(u.ultimo_login)[:16] if u.ultimo_login else "—",
            }
            for u in db.query(PanelUser).order_by(PanelUser.creato_il).all()
        ]
    finally:
        db.close()


@admin_required
def lista_admins(request):
    return render(request, "pages/admin_panel.html", {
        "panel_utenti": _lista_utenti_panel(),
        "current_user": get_current_user(request),
        "page": "admin",
    })


@admin_required
@require_http_methods(["POST"])
def crea_admin(request):
    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "").strip()
    nome     = request.POST.get("nome", "").strip() or None
    ruolo    = request.POST.get("ruolo", "viewer")

    error = None
    if not username or not password:
        error = "Username e password sono obbligatori."
    elif len(password) < 6:
        error = "La password deve essere di almeno 6 caratteri."
    else:
        db = SyncSessionLocal()
        try:
            if db.query(PanelUser).filter_by(username=username).first():
                error = f"Username '{username}' già in uso."
            else:
                db.add(PanelUser(
                    username=username,
                    password_hash=hash_password(password),
                    nome=nome,
                    ruolo=ruolo,
                ))
                db.commit()
        finally:
            db.close()

    if error:
        return render(request, "pages/admin_panel.html", {
            "panel_utenti": _lista_utenti_panel(),
            "current_user": get_current_user(request),
            "page": "admin",
            "error": error,
            "form_open": True,
        })
    return redirect("admin_lista")


@admin_required
@require_POST
def elimina_admin(request, uid: int):
    current = get_current_user(request)
    if current and current.id == uid:
        return redirect("admin_lista")
    db = SyncSessionLocal()
    try:
        u = db.query(PanelUser).filter_by(id=uid).first()
        if u:
            db.delete(u)
            db.commit()
    finally:
        db.close()
    return redirect("admin_lista")


@admin_required
@require_POST
def toggle_admin(request, uid: int):
    current = get_current_user(request)
    if current and current.id == uid:
        return redirect("admin_lista")
    db = SyncSessionLocal()
    try:
        u = db.query(PanelUser).filter_by(id=uid).first()
        if u:
            u.attivo = not u.attivo
            db.commit()
    finally:
        db.close()
    return redirect("admin_lista")


@login_required
def profilo(request):
    return render(request, "pages/profilo.html", {
        "current_user": get_current_user(request),
        "page": "profilo",
    })


@login_required
@require_POST
def cambia_password(request):
    current = get_current_user(request)
    vecchia  = request.POST.get("vecchia_password", "")
    nuova    = request.POST.get("nuova_password", "")
    conferma = request.POST.get("conferma_password", "")

    error = success = None

    if not verifica_password(vecchia, current.password_hash):
        error = "Password attuale non corretta."
    elif len(nuova) < 6:
        error = "La nuova password deve essere di almeno 6 caratteri."
    elif nuova != conferma:
        error = "Le password non coincidono."
    else:
        db = SyncSessionLocal()
        try:
            u = db.query(PanelUser).filter_by(id=current.id).first()
            if u:
                u.password_hash = hash_password(nuova)
                db.commit()
            success = "Password aggiornata con successo."
        finally:
            db.close()

    return render(request, "pages/profilo.html", {
        "current_user": get_current_user(request),
        "page": "profilo",
        "error": error,
        "success": success,
    })
