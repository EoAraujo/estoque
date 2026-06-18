"""Formulários do módulo de estoque (entradas, saídas, ajustes)."""
from decimal import Decimal

from django import forms
from django.utils import timezone

from core.models import Fornecedor, Produto
from .models import Lote, Movimento
from .services import EstoqueError


class BaseMovimentoForm(forms.Form):
    """Campos comuns a todas as movimentações."""
    produto = forms.ModelChoiceField(
        queryset=Produto.objects.filter(ativo=True).select_related("categoria"),
        label="Produto",
    )
    quantidade = forms.DecimalField(
        max_digits=12, decimal_places=3, min_value=Decimal("0.001"),
        label="Quantidade",
    )
    observacoes = forms.CharField(
        label="Observações", required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, **kwargs):
        # CreateView passa `instance=None` por padrão; ignoramos
        kwargs.pop("instance", None)
        kwargs.pop("files", None)
        super().__init__(*args, **kwargs)
        estilo = (
            "mt-1 block w-full rounded-md border-gray-300 shadow-sm "
            "focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
        )
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault(
                    "class",
                    "rounded border-gray-300 text-emerald-600 shadow-sm focus:ring-emerald-500"
                )
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("class", estilo + " min-h-[60px]")
            else:
                field.widget.attrs.setdefault("class", estilo)


class EntradaForm(BaseMovimentoForm):
    """Formulário para registrar uma entrada de estoque."""
    numero_lote = forms.CharField(label="Número do lote", required=False, max_length=80)
    data_fabricacao = forms.DateField(required=False, label="Data de fabricação",
                                       widget=forms.DateInput(attrs={"type": "date"}))
    data_validade = forms.DateField(required=False, label="Data de validade *",
                                     widget=forms.DateInput(attrs={"type": "date"}))
    data_entrada = forms.DateField(
        required=False, label="Data de entrada",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    valor_unitario = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"),
        required=False, label="Valor unitário (R$)",
    )
    fornecedor = forms.ModelChoiceField(
        queryset=Fornecedor.objects.filter(ativo=True),
        required=False, label="Fornecedor",
        empty_label="— Sem fornecedor —",
    )
    nota_fiscal = forms.CharField(label="Nota fiscal", required=False, max_length=50)
    motivo = forms.ChoiceField(
        choices=Movimento.MOTIVO_ENTRADA_CHOICES,
        initial="COMPRA", label="Motivo",
    )

    def clean(self):
        cleaned = super().clean()
        produto = cleaned.get("produto")
        if produto and produto.controla_validade and not cleaned.get("data_validade"):
            self.add_error("data_validade",
                           f"O produto '{produto.nome}' exige data de validade.")
        if not cleaned.get("data_entrada"):
            cleaned["data_entrada"] = timezone.localdate()
        return cleaned


class SaidaForm(BaseMovimentoForm):
    """Formulário para registrar uma saída de estoque."""
    motivo = forms.ChoiceField(
        choices=Movimento.MOTIVO_SAIDA_CHOICES,
        initial="PRODUCAO", label="Motivo",
    )
    responsavel = forms.CharField(
        label="Responsável / Setor", required=False, max_length=120,
    )
    lote = forms.ModelChoiceField(
        queryset=Lote.objects.none(),
        required=False, label="Lote (opcional)",
        help_text="Se vazio, o sistema consome do lote que vence primeiro (FEFO).",
        empty_label="— Automático (FEFO) —",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Atualiza queryset do lote se produto foi selecionado
        produto_id = None
        if self.data.get("produto"):
            try:
                produto_id = int(self.data.get("produto"))
            except (ValueError, TypeError):
                produto_id = None
        elif self.initial.get("produto"):
            produto_id = self.initial["produto"].pk
        elif self.fields["produto"].queryset:
            pass
        if produto_id:
            self.fields["lote"].queryset = (
                Lote.objects
                .filter(produto_id=produto_id, ativo=True, quantidade_atual__gt=0)
                .order_by("data_validade", "data_entrada")
            )

    def clean(self):
        cleaned = super().clean()
        produto = cleaned.get("produto")
        quantidade = cleaned.get("quantidade")
        if produto and quantidade:
            if produto.quantidade_atual < quantidade:
                self.add_error(
                    "quantidade",
                    f"Estoque insuficiente. Disponível: "
                    f"{produto.quantidade_atual} {produto.unidade_medida}."
                )
        return cleaned


class AjusteForm(forms.Form):
    """Formulário para ajuste manual de inventário."""
    DIRECAO_CHOICES = [
        ("ENTRADA", "Adicionar ao estoque (contagem maior que o sistema)"),
        ("SAIDA", "Remover do estoque (contagem menor que o sistema)"),
    ]
    MOTIVO_CHOICES = [
        ("INVENTARIO", "Inventário / Contagem"),
        ("CORRECAO_LANCAMENTO", "Correção de lançamento"),
        ("DANO", "Produto danificado"),
        ("VALIDADE_VENCIDA", "Vencimento identificado tardiamente"),
        ("OUTRO", "Outro"),
    ]

    produto = forms.ModelChoiceField(
        queryset=Produto.objects.filter(ativo=True),
        label="Produto",
    )
    direcao = forms.ChoiceField(choices=DIRECAO_CHOICES, label="Direção do ajuste",
                                widget=forms.RadioSelect)
    quantidade = forms.DecimalField(
        max_digits=12, decimal_places=3, min_value=Decimal("0.001"),
        label="Quantidade a ajustar",
    )
    motivo = forms.ChoiceField(choices=MOTIVO_CHOICES, label="Motivo do ajuste")
    observacoes = forms.CharField(
        label="Justificativa / Observações",
        widget=forms.Textarea(attrs={"rows": 3}),
        required=True,
    )
    lote = forms.ModelChoiceField(
        queryset=Lote.objects.none(),
        required=False, label="Lote (para saída)",
        help_text="Obrigatório ao remover de um lote específico.",
        empty_label="— Selecione —",
    )

    def __init__(self, *args, **kwargs):
        kwargs.pop("instance", None)
        kwargs.pop("files", None)
        super().__init__(*args, **kwargs)
        estilo = (
            "mt-1 block w-full rounded-md border-gray-300 shadow-sm "
            "focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
        )
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                field.widget.attrs.setdefault(
                    "class",
                    "rounded border-gray-300 text-emerald-600 shadow-sm focus:ring-emerald-500"
                )
            elif isinstance(widget, forms.RadioSelect):
                field.widget.attrs.setdefault("class", "mt-2 space-y-2")
            elif isinstance(widget, forms.Textarea):
                field.widget.attrs.setdefault("class", estilo + " min-h-[80px]")
            else:
                field.widget.attrs.setdefault("class", estilo)

        # Atualiza queryset do lote conforme produto
        produto_id = self.data.get("produto")
        if not produto_id and self.initial.get("produto"):
            produto_id = self.initial["produto"].pk
        if produto_id:
            self.fields["lote"].queryset = (
                Lote.objects
                .filter(produto_id=produto_id, ativo=True, quantidade_atual__gt=0)
                .order_by("data_validade", "data_entrada")
            )

    def clean(self):
        cleaned = super().clean()
        direcao = cleaned.get("direcao")
        lote = cleaned.get("lote")
        produto = cleaned.get("produto")
        quantidade = cleaned.get("quantidade")
        if direcao == "SAIDA" and produto and quantidade:
            if not lote:
                self.add_error("lote", "Selecione o lote do qual será feita a remoção.")
            elif lote.quantidade_atual < quantidade:
                self.add_error("quantidade",
                               f"Quantidade maior que o saldo do lote "
                               f"({lote.quantidade_atual}).")
        return cleaned


class CancelarMovimentoForm(forms.Form):
    motivo_cancelamento = forms.CharField(
        label="Motivo do cancelamento",
        widget=forms.Textarea(attrs={"rows": 3, "minlength": 10}),
        min_length=10,
        help_text="Mínimo 10 caracteres. Esta ação não pode ser desfeita.",
    )

    def __init__(self, *args, **kwargs):
        kwargs.pop("instance", None)
        kwargs.pop("files", None)
        super().__init__(*args, **kwargs)
        estilo = (
            "mt-1 block w-full rounded-md border-gray-300 shadow-sm "
            "focus:border-red-500 focus:ring-red-500 sm:text-sm"
        )
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", estilo + " min-h-[80px]")


class FiltroMovimentoForm(forms.Form):
    TIPO_CHOICES = [("", "Todos")] + Movimento.TIPO_CHOICES
    busca = forms.CharField(required=False, label="Buscar")
    tipo = forms.ChoiceField(choices=TIPO_CHOICES, required=False, label="Tipo")
    produto = forms.ModelChoiceField(
        queryset=Produto.objects.filter(ativo=True),
        required=False, empty_label="Todos os produtos",
    )
    data_inicio = forms.DateField(
        required=False, label="De",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    data_fim = forms.DateField(
        required=False, label="Até",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    cancelado = forms.ChoiceField(
        required=False, label="Status",
        choices=[("", "Todos"), ("False", "Ativos"), ("True", "Cancelados")],
    )

    def __init__(self, *args, **kwargs):
        kwargs.pop("instance", None)
        kwargs.pop("files", None)
        super().__init__(*args, **kwargs)
        estilo = (
            "mt-1 block w-full rounded-md border-gray-300 shadow-sm "
            "focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
        )
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", estilo)
