"""
web/core/views_admin_panel.py — Gestione utenti del web panel (solo admin).
Usa django.contrib.auth.User nativo — niente PanelUser, niente crypto custom.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods, require_POST

from web.core.auth import admin_required, login_required, get_current_user

User = get_user_model()


def _serialize_user(u) -> dict:
    return {
        "id":           u.id,
        "username":     u.username,
        "nome":         u.get_full_name() or u.username,
        "ruolo":        "admin" if u.is_superuser else ("staff" if u.is_staff else "viewer"),
        "attivo":       u.is_active,
        "creato_il":    u.date_joined.strftime("%Y-%m-%d %H:%M") if u.date_joined else "—",
        "ultimo_login": u.last_login.strftime("%Y-%m-%d %H:%M") if u.last_login else "—",
    }


def _lista_panel_users() -> list:
    return [_serialize_user(u) for u in User.objects.order_by("date_joined")]


# ── Lista e creazione ─────────────────────────────────────────────────────────

@admin_required
def lista_admins(request):
    return render(request, "pages/admin_panel.html", {
        "panel_utenti": _lista_panel_users(),
        "current_user": get_current_user(request),
        "page": "admin",
    })


@admin_required
@require_http_methods(["POST"])
def crea_admin(request):
    username  = request.POST.get("username", "").strip()
    password  = request.POST.get("password", "").strip()
    nome      = request.POST.get("nome", "").strip()
    ruolo     = request.POST.get("ruolo", "viewer")   # viewer | staff | admin

    error = None

    if not username or not password:
        error = "Username e password sono obbligatori."
    elif User.objects.filter(username=username).exists():
        error = f"Username '{username}' già in uso."
    else:
        # Valida la password con i validator Django (lunghezza, complessità…)
        try:
            validate_password(password)
        except ValidationError as e:
            error = " ".join(e.messages)

    if not error:
        first_name = nome.split()[0] if nome else ""
        last_name  = " ".join(nome.split()[1:]) if nome else ""
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=ruolo in ("staff", "admin"),
            is_superuser=ruolo == "admin",
        )

    if error:
        return render(request, "pages/admin_panel.html", {
            "panel_utenti": _lista_panel_users(),
            "current_user": get_current_user(request),
            "page":       "admin",
            "error":      error,
            "form_open":  True,
        })

    return redirect("admin_lista")


# ── Eliminazione e toggle ─────────────────────────────────────────────────────

@admin_required
@require_POST
def elimina_admin(request, uid: int):
    current = get_current_user(request)
    # Impedisce l'auto-eliminazione
    if current and current.id == uid:
        return redirect("admin_lista")
    User.objects.filter(id=uid).delete()
    return redirect("admin_lista")


@admin_required
@require_POST
def toggle_admin(request, uid: int):
    current = get_current_user(request)
    if current and current.id == uid:
        return redirect("admin_lista")
    try:
        u = User.objects.get(id=uid)
        u.is_active = not u.is_active
        u.save(update_fields=["is_active"])
    except User.DoesNotExist:
        pass
    return redirect("admin_lista")


# ── Profilo e cambio password ─────────────────────────────────────────────────

@login_required
def profilo(request):
    return render(request, "pages/profilo.html", {
        "current_user": get_current_user(request),
        "page": "profilo",
    })


@login_required
@require_POST
def cambia_password(request):
    user     = get_current_user(request)
    vecchia  = request.POST.get("vecchia_password", "")
    nuova    = request.POST.get("nuova_password", "")
    conferma = request.POST.get("conferma_password", "")

    error = success = None

    if not user.check_password(vecchia):
        # check_password() è timing-safe — Django nativo
        error = "Password attuale non corretta."
    elif nuova != conferma:
        error = "Le password non coincidono."
    else:
        try:
            validate_password(nuova, user=user)
        except ValidationError as e:
            error = " ".join(e.messages)

    if not error:
        user.set_password(nuova)
        user.save()
        # Aggiorna la sessione per non fare il logout automatico dopo il cambio
        update_session_auth_hash(request, user)
        success = "Password aggiornata con successo."

    return render(request, "pages/profilo.html", {
        "current_user": get_current_user(request),
        "page":    "profilo",
        "error":   error,
        "success": success,
    })
