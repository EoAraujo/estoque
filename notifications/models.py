"""Modelos de notificações (Fase 5)."""
from django.conf import settings
from django.db import models


class WebPushSubscription(models.Model):
    """Subscription de Web Push de um usuário/dispositivo."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
        verbose_name="Usuário",
    )
    endpoint = models.URLField("Endpoint", max_length=500, unique=True)
    p256dh = models.CharField("Chave pública (p256dh)", max_length=200)
    auth = models.CharField("Auth secret", max_length=100)
    user_agent = models.CharField("User-Agent", max_length=255, blank=True)
    ativo = models.BooleanField("Ativo", default=True)
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Subscription de Web Push"
        verbose_name_plural = "Subscriptions de Web Push"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.user.username} — {self.endpoint[:50]}…"
