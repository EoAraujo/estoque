"""
Modelos do módulo de estoque.

Lote:    cada unidade de entrada com validade e número de lote próprios.
Movimento: registro imutável de entrada ou saída (nunca apagado).
Alerta:   notificações geradas automaticamente pelo sistema.
"""
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from core.models import Fornecedor, Produto, TimeStampedModel


class Lote(TimeStampedModel):
    """
    Lote de um produto com sua própria data de validade e quantidade.

    Um mesmo produto pode ter vários lotes simultâneos em estoque.
    As saídas consomem lotes seguindo a regra PEPS (Primeiro a Entrar,
    Primeiro a Sair) ou FEFO (Primeiro a Vencer, Primeiro a Sair).
    """
    produto = models.ForeignKey(
        Produto, on_delete=models.PROTECT,
        related_name="lotes", verbose_name="Produto",
    )
    numero_lote = models.CharField("Número do lote", max_length=80, blank=True)
    data_fabricacao = models.DateField("Data de fabricação", null=True, blank=True)
    data_validade = models.DateField("Data de validade", null=True, blank=True)
    data_entrada = models.DateField("Data de entrada")

    quantidade_inicial = models.DecimalField(
        "Quantidade inicial", max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
    )
    quantidade_atual = models.DecimalField(
        "Quantidade atual", max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
    )

    nota_fiscal = models.CharField("Nota fiscal", max_length=50, blank=True)
    observacoes = models.CharField("Observações", max_length=255, blank=True)
    ativo = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "Lote"
        verbose_name_plural = "Lotes"
        ordering = ["data_validade", "data_entrada"]
        indexes = [
            models.Index(fields=["produto", "data_validade"]),
            models.Index(fields=["data_validade"]),
        ]

    def __str__(self):
        validade = self.data_validade.strftime("%d/%m/%Y") if self.data_validade else "s/ validade"
        return f"{self.produto.nome} • Lote {self.numero_lote or '—'} • Val. {validade}"

    @property
    def dias_para_vencer(self):
        if not self.data_validade:
            return None
        from django.utils import timezone
        return (self.data_validade - timezone.localdate()).days

    @property
    def vencido(self):
        d = self.dias_para_vencer
        return d is not None and d < 0


class Movimento(TimeStampedModel):
    """
    Registro imutável de uma movimentação de estoque.

    O sistema NUNCA apaga movimentos. Para corrigir, faz-se um
    movimento de ajuste (entrada ou saída) com observações
    explicando a correção.
    """
    TIPO_CHOICES = [
        ("ENTRADA", "Entrada"),
        ("SAIDA", "Saída"),
    ]

    MOTIVO_ENTRADA_CHOICES = [
        ("COMPRA", "Compra / Nota fiscal"),
        ("DEVOLUCAO", "Devolução"),
        ("AJUSTE_ENTRADA", "Ajuste de inventário (entrada)"),
        ("TRANSFERENCIA_IN", "Transferência (entrada)"),
        ("INICIAL", "Estoque inicial"),
        ("OUTRO_E", "Outro"),
    ]

    MOTIVO_SAIDA_CHOICES = [
        ("PRODUCAO", "Produção / Consumo"),
        ("CONSUMO_INTERNO", "Consumo interno"),
        ("DESCARTE", "Descarte"),
        ("PERDA", "Perda / Quebra"),
        ("TRANSFERENCIA_OUT", "Transferência (saída)"),
        ("AJUSTE_SAIDA", "Ajuste de inventário (saída)"),
        ("VENCIMENTO", "Vencimento"),
        ("OUTRO_S", "Outro"),
    ]

    produto = models.ForeignKey(
        Produto, on_delete=models.PROTECT,
        related_name="movimentos", verbose_name="Produto",
    )
    lote = models.ForeignKey(
        Lote, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="movimentos", verbose_name="Lote",
    )
    tipo = models.CharField("Tipo", max_length=8, choices=TIPO_CHOICES)
    motivo = models.CharField("Motivo", max_length=30)
    quantidade = models.DecimalField(
        "Quantidade", max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )

    # Campos de entrada
    valor_unitario = models.DecimalField(
        "Valor unitário (R$)", max_digits=12, decimal_places=2,
        null=True, blank=True,
    )
    valor_total = models.DecimalField(
        "Valor total (R$)", max_digits=12, decimal_places=2,
        null=True, blank=True,
    )
    fornecedor = models.ForeignKey(
        Fornecedor, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="movimentos", verbose_name="Fornecedor",
    )
    nota_fiscal = models.CharField("Nota fiscal", max_length=50, blank=True)

    # Campos de saída
    responsavel = models.CharField("Responsável / Setor", max_length=120, blank=True)

    data_movimento = models.DateTimeField("Data do movimento")

    observacoes = models.TextField("Observações", blank=True)
    cancelado = models.BooleanField("Cancelado", default=False)
    motivo_cancelamento = models.CharField(
        "Motivo do cancelamento", max_length=255, blank=True,
    )

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"
        ordering = ["-data_movimento"]
        indexes = [
            models.Index(fields=["produto", "-data_movimento"]),
            models.Index(fields=["tipo", "-data_movimento"]),
            models.Index(fields=["-data_movimento"]),
        ]

    def __str__(self):
        sinal = "+" if self.tipo == "ENTRADA" else "-"
        return f"{self.data_movimento:%d/%m/%Y} • {self.produto.nome} • {sinal}{self.quantidade}"

    def save(self, *args, **kwargs):
        if self.valor_unitario and self.quantidade and self.valor_total is None:
            self.valor_total = (self.valor_unitario * self.quantidade).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)


class Alerta(TimeStampedModel):
    """Notificações geradas automaticamente pelo motor de inteligência."""
    NIVEL_CHOICES = [
        ("INFO", "Informativo"),
        ("ATENCAO", "Atenção"),
        ("URGENTE", "Urgente"),
        ("CRITICO", "Crítico"),
    ]

    TIPO_CHOICES = [
        ("ESTOQUE_MIN", "Estoque no mínimo"),
        ("ESTOQUE_CRITICO", "Estoque crítico"),
        ("ESGOTADO", "Produto esgotado"),
        ("RUPTURA", "Risco de ruptura"),
        ("VENCIDO", "Produto vencido"),
        ("VENCIMENTO_30", "Vencimento em 30 dias"),
        ("VENCIMENTO_15", "Vencimento em 15 dias"),
        ("VENCIMENTO_7", "Vencimento em 7 dias"),
        ("VENCIMENTO_3", "Vencimento em 3 dias"),
        ("RISCO_PERDA", "Risco de perda por vencimento"),
        ("EXCESSO", "Estoque em excesso"),
        ("CONSUMO_ALTO", "Consumo acima da média"),
        ("CONSUMO_BAIXO", "Consumo abaixo da média"),
        ("COMPRA", "Compra necessária"),
        ("COMPRA_URGENTE", "Compra urgente"),
        ("PRECO_SUBIU", "Aumento significativo de preço"),
        ("PRECO_DESCEU", "Redução significativa de preço"),
    ]

    tipo = models.CharField("Tipo", max_length=20, choices=TIPO_CHOICES)
    nivel = models.CharField("Nível", max_length=10, choices=NIVEL_CHOICES)
    produto = models.ForeignKey(
        Produto, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="alertas", verbose_name="Produto",
    )
    lote = models.ForeignKey(
        Lote, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="alertas", verbose_name="Lote",
    )
    titulo = models.CharField("Título", max_length=200)
    mensagem = models.TextField("Mensagem", blank=True)
    lido = models.BooleanField("Lido", default=False)
    resolvido = models.BooleanField("Resolvido", default=False)
    dados = models.JSONField("Dados extras", default=dict, blank=True)

    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lido", "-created_at"]),
            models.Index(fields=["tipo"]),
        ]

    def __str__(self):
        return f"[{self.nivel}] {self.titulo}"
