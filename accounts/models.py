"""Modelo de extensão para o usuário padrão do Django."""
from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """Dados extras do usuário."""
    PERIODO_CHOICES = [
        (7, "Últimos 7 dias"),
        (15, "Últimos 15 dias"),
        (30, "Últimos 30 dias"),
        (90, "Últimos 90 dias"),
        (180, "Últimos 6 meses"),
        (365, "Último ano"),
    ]
    PERIODO_PADRAO = 30

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    telefone = models.CharField("Telefone", max_length=30, blank=True)
    cargo = models.CharField("Cargo / Função", max_length=100, blank=True)
    observacoes = models.TextField("Observações", blank=True)
    deve_trocar_senha = models.BooleanField(
        "Deve trocar senha no próximo login", default=False,
    )
    periodo_padrao = models.PositiveIntegerField(
        "Período padrão para análise (dias)",
        choices=PERIODO_CHOICES, default=PERIODO_PADRAO,
        help_text="Usado no dashboard, gráficos e relatórios.",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de usuário"
        verbose_name_plural = "Perfis de usuário"

    def __str__(self):
        return self.user.get_full_name() or self.user.username

