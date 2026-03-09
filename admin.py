from django.contrib import admin
from .models import Channel, Message, BotLog


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ["name", "channel_id", "username", "is_active", "added_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "username"]
    list_editable = ["is_active"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["pk", "channel", "status", "telegram_message_id", "created_at"]
    list_filter = ["status", "channel"]
    search_fields = ["content"]
    readonly_fields = ["created_at", "published_at"]


@admin.register(BotLog)
class BotLogAdmin(admin.ModelAdmin):
    list_display = ["level", "message", "created_at"]
    list_filter = ["level"]
    search_fields = ["message"]
    readonly_fields = ["created_at"]
