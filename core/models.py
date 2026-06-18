"""
Modelos centrais do sistema.

Define as entidades de cadastro base (Categoria, Fornecedor, Produto)
e configurações globais.
"""
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class TimeStampedModel(models.Model):
    """Abstrato: campos de auditoria padrão em todas as tabelas."""
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="%(class)s_criados",
        verbose_name="Criado por",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="%(class)s_atualizados",
        verbose_name="Atualizado por",
    )

    class Meta:
        abstract = True


class ConfiguracaoSingleton(models.Model):
    """Configurações globais do sistema. Existe apenas um registro."""
    empresa_nome = models.CharField("Nome da empresa", max_length=200, blank=True)
    empresa_cnpj = models.CharField("CNPJ", max_length=20, blank=True)
    empresa_telefone = models.CharField("Telefone", max_length=30, blank=True)
    empresa_endereco = models.CharField("Endereço", max_length=255, blank=True)

    # Alertas de validade (em dias)
    alerta_vencimento_30 = models.PositiveIntegerField(default=30)
    alerta_vencimento_15 = models.PositiveIntegerField(default=15)
    alerta_vencimento_7 = models.PositiveIntegerField(default=7)
    alerta_vencimento_3 = models.PositiveIntegerField(default=3)

    # Janela para cálculo de consumo médio (em dias)
    janela_consumo_dias = models.PositiveIntegerField(
        "Janela de cálculo de consumo (dias)", default=30,
        help_text="Período usado para calcular consumo médio",
    )

    class Meta:
        verbose_name = "Configuração"
        verbose_name_plural = "Configurações"

    def save(self, *args, **kwargs):
        """Garante que só exista um registro (singleton)."""
        if not self.pk and ConfiguracaoSingleton.objects.exists():
            existing = ConfiguracaoSingleton.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        """Retorna a instância única, criando-a se não existir."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Configurações do sistema"


class Categoria(TimeStampedModel):
    """Categoria de produto (ex: Hortifruti, Carnes, Limpeza)."""
    nome = models.CharField("Nome", max_length=100, unique=True)
    descricao = models.TextField("Descrição", blank=True)
    ativa = models.BooleanField("Ativa", default=True)
    cor = models.CharField(
        "Cor de identificação", max_length=7, blank=True,
        help_text="Código hexadecimal (#RRGGBB) usado no dashboard",
    )

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Fornecedor(TimeStampedModel):
    """Fornecedor de produtos."""
    nome = models.CharField("Nome / Razão Social", max_length=200)
    nome_fantasia = models.CharField("Nome fantasia", max_length=200, blank=True)
    cnpj = models.CharField("CNPJ", max_length=20, blank=True)
    inscricao_estadual = models.CharField("Inscrição Estadual", max_length=30, blank=True)

    contato_nome = models.CharField("Nome do contato", max_length=120, blank=True)
    telefone = models.CharField("Telefone", max_length=30, blank=True)
    email = models.EmailField("E-mail", blank=True)

    endereco = models.CharField("Endereço", max_length=255, blank=True)
    cidade = models.CharField("Cidade", max_length=100, blank=True)
    estado = models.CharField("UF", max_length=2, blank=True)
    cep = models.CharField("CEP", max_length=10, blank=True)

    lead_time_days = models.PositiveIntegerField(
        "Prazo de reposição (dias)", default=7,
        help_text="Tempo médio de entrega do fornecedor",
    )
    observacoes = models.TextField("Observações", blank=True)
    ativo = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "Fornecedor"
        verbose_name_plural = "Fornecedores"
        ordering = ["nome"]

    def __str__(self):
        return self.nome_fantasia or self.nome


class Produto(TimeStampedModel):
    """
    Produto do estoque. Suporta múltiplos lotes e datas de validade
    (relacionamento definido em stock.Lote).
    """
    UNIDADE_CHOICES = [
        ("KG", "Quilograma (kg)"),
        ("G", "Grama (g)"),
        ("L", "Litro (L)"),
        ("ML", "Mililitro (mL)"),
        ("UN", "Unidade"),
        ("CX", "Caixa"),
        ("PC", "Pacote"),
        ("DZ", "Dúzia"),
        ("FD", "Fardo"),
    ]

    nome = models.CharField("Nome", max_length=200)
    codigo_interno = models.CharField("Código interno", max_length=50, unique=True)
    codigo_barras = models.CharField("Código de barras", max_length=50, blank=True)

    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT,
        related_name="produtos", verbose_name="Categoria",
    )
    fornecedor_principal = models.ForeignKey(
        Fornecedor, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="produtos", verbose_name="Fornecedor principal",
    )

    unidade_medida = models.CharField(
        "Unidade de medida", max_length=3,
        choices=UNIDADE_CHOICES, default="UN",
    )
    controla_validade = models.BooleanField(
        "Controla validade", default=True,
        help_text="Se marcado, o sistema exigirá lote e data de validade nas entradas",
    )

    estoque_minimo = models.DecimalField(
        "Estoque mínimo", max_digits=12, decimal_places=3, default=Decimal("0"),
        help_text="Quantidade mínima antes de alertar compra",
    )
    estoque_ideal = models.DecimalField(
        "Estoque ideal", max_digits=12, decimal_places=3, default=Decimal("0"),
        help_text="Quantidade desejada após reposição",
    )

    localizacao = models.CharField(
        "Localização física", max_length=100, blank=True,
        help_text="Ex: Prateleira A3, Câmara fria 2",
    )
    observacoes = models.TextField("Observações", blank=True)
    ativo = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ["nome"]
        indexes = [
            models.Index(fields=["codigo_interno"]),
            models.Index(fields=["nome"]),
            models.Index(fields=["categoria"]),
        ]

    def __str__(self):
        return f"{self.nome} ({self.codigo_interno})"

    def clean(self):
        if self.estoque_minimo < 0:
            raise ValidationError({"estoque_minimo": "Estoque mínimo não pode ser negativo."})
        if self.estoque_ideal < 0:
            raise ValidationError({"estoque_ideal": "Estoque ideal não pode ser negativo."})
        if self.estoque_ideal and self.estoque_minimo and self.estoque_ideal < self.estoque_minimo:
            raise ValidationError(
                {"estoque_ideal": "Estoque ideal deve ser maior ou igual ao estoque mínimo."}
            )

    @property
    def quantidade_atual(self):
        """
        Estoque atual do produto, calculado a partir do histórico
        de movimentações (entradas − saídas), excluindo canceladas.
        Esta é a fonte da verdade para a quantidade em estoque.
        """
        from stock.models import Movimento
        total = Movimento.objects.filter(
            produto=self, cancelado=False,
        ).aggregate(
            entradas=models.Sum("quantidade", filter=models.Q(tipo="ENTRADA")),
            saidas=models.Sum("quantidade", filter=models.Q(tipo="SAIDA")),
        )
        e = total["entradas"] or Decimal("0")
        s = total["saidas"] or Decimal("0")
        return e - s
