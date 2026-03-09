from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Main
    path("", views.dashboard, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),

    # Channels
    path("channels/", views.channels_view, name="channels"),
    path("channels/<int:channel_id>/toggle/", views.channel_toggle, name="channel_toggle"),
    path("channels/<int:channel_id>/delete/", views.channel_delete, name="channel_delete"),

    # Messages
    path("messages/", views.messages_view, name="messages"),
    path("messages/publish/", views.publish_message, name="publish_message"),

    # Logs
    path("logs/", views.logs_view, name="logs"),

    # API
    path("api/stats/", views.api_stats, name="api_stats"),
]
