from django.db import models
from django.utils import timezone


class Channel(models.Model):
    channel_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=255)
    username = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.name} ({self.channel_id})"


class Message(models.Model):
    STATUS_CHOICES = [
        ("pending", "In attesa"),
        ("published", "Pubblicato"),
        ("failed", "Fallito"),
        ("removed", "Rimosso"),
    ]

    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="messages")
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    telegram_message_id = models.BigIntegerField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Msg #{self.pk} → {self.channel.name} [{self.status}]"


class BotLog(models.Model):
    LEVEL_CHOICES = [
        ("INFO", "Info"),
        ("WARNING", "Warning"),
        ("ERROR", "Error"),
        ("DEBUG", "Debug"),
    ]
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default="INFO")
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.level}] {self.created_at:%Y-%m-%d %H:%M} — {self.message[:60]}"
