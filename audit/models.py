"""Modelos de auditoria."""
from django.conf import settings
from django.db import models


class LogAuditoria(models.Model):
    """
    Registro imutável de uma ação executada no sistema.
    Criado automaticamente via signals/middleware.
    """
    ACAO_CHOICES = [
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
        ("CRIAR", "Criou registro"),
        ("EDITAR", "Editou registro"),
        ("EXCLUIR", "Excluiu registro"),
        ("MOVER", "Movimentou estoque"),
        ("CANCELAR", "Cancelou registro"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="logs_auditoria",
        verbose_name="Usuário",
    )
    acao = models.CharField("Ação", max_length=20, choices=ACAO_CHOICES)
    modelo = models.CharField("Modelo", max_length=100, blank=True)
    objeto_id = models.CharField("ID do objeto", max_length=64, blank=True)
    objeto_repr = models.CharField("Descrição do objeto", max_length=255, blank=True)
    dados_anteriores = models.JSONField("Dados anteriores", default=dict, blank=True)
    dados_novos = models.JSONField("Dados novos", default=dict, blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.CharField("User-Agent", max_length=255, blank=True)
    url = models.CharField("URL", max_length=255, blank=True)
    metodo = models.CharField("Método HTTP", max_length=10, blank=True)
    timestamp = models.DateTimeField("Quando", auto_now_add=True)

    class Meta:
        verbose_name = "Log de auditoria"
        verbose_name_plural = "Logs de auditoria"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["modelo", "objeto_id"]),
        ]

    def __str__(self):
        return f"{self.timestamp:%d/%m/%Y %H:%M} • {self.usuario or 'sistema'} • {self.acao}"

    def has_delete_permission(self, request, obj=None):
        # Logs são imutáveis
        return False
