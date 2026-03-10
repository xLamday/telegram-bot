"""
web/core/views_auth.py — Login e logout del web panel.
"""
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from database.session import SyncSessionLocal
from database.models import PanelUser
from web.core.auth import (
    verifica_password, login_user, logout_user,
    get_current_user, seed_admin_if_missing,
)
from datetime import datetime


@require_http_methods(["GET", "POST"])
def login_view(request):
    if get_current_user(request):
        return redirect("dashboard")

    seed_admin_if_missing()
    error = None

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        db = SyncSessionLocal()
        try:
            user = db.query(PanelUser).filter_by(username=username).first()
            if user:
                db.expunge(user)
        finally:
            db.close()

        if user and user.attivo and verifica_password(password, user.password_hash):
            # Aggiorna ultimo_login
            db2 = SyncSessionLocal()
            try:
                u = db2.query(PanelUser).filter_by(id=user.id).first()
                if u:
                    u.ultimo_login = datetime.utcnow()
                db2.commit()
            finally:
                db2.close()

            login_user(request, user)
            return redirect("dashboard")
        else:
            error = "Credenziali non valide o account disabilitato."

    return render(request, "pages/login.html", {"error": error})


def logout_view(request):
    logout_user(request)
    return redirect("login")
