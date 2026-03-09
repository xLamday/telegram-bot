import httpx
from django.conf import settings
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Channel, Message, BotLog

FASTAPI_URL = settings.FASTAPI_BASE_URL


# ─── Auth ──────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    error = None
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password"),
        )
        if user:
            login(request, user)
            return redirect("dashboard")
        error = "Credenziali non valide."
    return render(request, "login.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("login")


# ─── Dashboard ─────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    stats = {
        "channels": Channel.objects.filter(is_active=True).count(),
        "messages_total": Message.objects.count(),
        "messages_published": Message.objects.filter(status="published").count(),
        "messages_failed": Message.objects.filter(status="failed").count(),
    }
    recent_messages = Message.objects.select_related("channel").order_by("-created_at")[:10]
    recent_logs = BotLog.objects.order_by("-created_at")[:20]
    return render(request, "dashboard.html", {
        "stats": stats,
        "recent_messages": recent_messages,
        "recent_logs": recent_logs,
    })


# ─── Channels ──────────────────────────────────────────────────────────────────

@login_required
def channels_view(request):
    channels = Channel.objects.all()
    return render(request, "channels.html", {"channels": channels})


@login_required
@require_POST
def channel_toggle(request, channel_id):
    try:
        ch = Channel.objects.get(pk=channel_id)
        ch.is_active = not ch.is_active
        ch.save()
        return JsonResponse({"ok": True, "is_active": ch.is_active})
    except Channel.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Not found"}, status=404)


@login_required
@require_POST
def channel_delete(request, channel_id):
    try:
        ch = Channel.objects.get(pk=channel_id)
        ch.delete()
        return JsonResponse({"ok": True})
    except Channel.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Not found"}, status=404)


# ─── Messages ──────────────────────────────────────────────────────────────────

@login_required
def messages_view(request):
    messages = Message.objects.select_related("channel").all()
    channels = Channel.objects.filter(is_active=True)
    return render(request, "messages.html", {
        "messages": messages,
        "channels": channels,
    })


@login_required
@require_POST
def publish_message(request):
    """Invia richiesta di pubblicazione alla FastAPI → Bot Telegram."""
    try:
        data = json.loads(request.body)
        channel_id = data.get("channel_id")
        content = data.get("content", "").strip()
        if not channel_id or not content:
            return JsonResponse({"ok": False, "error": "Dati mancanti"}, status=400)

        # Chiama FastAPI
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{FASTAPI_URL}/api/messages/publish",
                json={"channel_id": int(channel_id), "content": content},
            )
            result = resp.json()

        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# ─── Logs ──────────────────────────────────────────────────────────────────────

@login_required
def logs_view(request):
    logs = BotLog.objects.all()[:200]
    return render(request, "logs.html", {"logs": logs})


# ─── API Bridge (Django → FastAPI stats) ───────────────────────────────────────

@login_required
def api_stats(request):
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(f"{FASTAPI_URL}/api/stats")
            return JsonResponse(resp.json())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=503)
