from django.urls import path
from . import views, views_auth, views_admin_panel

urlpatterns = [
    # Auth
    path("login/",   views_auth.login_view,   name="login"),
    path("logout/",  views_auth.logout_view,  name="logout"),

    # Panel principale
    path("",          views.dashboard, name="dashboard"),
    path("utenti/",   views.utenti,    name="utenti"),
    path("canali/",   views.canali,    name="canali"),
    path("messaggi/", views.messaggi,  name="messaggi"),
    path("logs/",     views.logs,      name="logs"),

    # Gestione admin panel (solo admin)
    path("amministratori/",                      views_admin_panel.lista_admins,   name="admin_lista"),
    path("amministratori/crea/",                 views_admin_panel.crea_admin,     name="admin_crea"),
    path("amministratori/<int:uid>/elimina/",    views_admin_panel.elimina_admin,  name="admin_elimina"),
    path("amministratori/<int:uid>/toggle/",     views_admin_panel.toggle_admin,   name="admin_toggle"),
    path("profilo/",                             views_admin_panel.profilo,        name="profilo"),
    path("profilo/password/",                    views_admin_panel.cambia_password,name="cambia_password"),
]
