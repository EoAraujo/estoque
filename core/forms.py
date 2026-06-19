from django import forms
from .models import Categoria, Fornecedor, Produto, ConfiguracaoSingleton


ESTILO_CAMPO = (
    "mt-1 block w-full rounded-md border-gray-300 shadow-sm "
    "focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
)


class FormBaseMixin:
    def aplicar_estilo(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput,)):
                widget.attrs.setdefault(
                    "class",
                    "rounded border-gray-300 text-emerald-600 "
                    "shadow-sm focus:ring-emerald-500"
                )
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", ESTILO_CAMPO)
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault(
                    "class",
                    ESTILO_CAMPO + " min-h-[80px]"
                )
            else:
                widget.attrs.setdefault("class", ESTILO_CAMPO)
            if not widget.attrs.get("placeholder") and field.label:
                widget.attrs["placeholder"] = field.label


class CategoriaForm(FormBaseMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nome", "descricao", "cor", "ativa"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilo()


class FornecedorForm(FormBaseMixin, forms.ModelForm):
    class Meta:
        model = Fornecedor
        fields = [
            "nome", "nome_fantasia", "cnpj", "inscricao_estadual",
            "contato_nome", "telefone", "email",
            "endereco", "cidade", "estado", "cep",
            "lead_time_days", "observacoes", "ativo",
        ]
        widgets = {
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilo()


class ProdutoForm(FormBaseMixin, forms.ModelForm):
    class Meta:
        model = Produto
        fields = [
            "nome", "codigo_interno", "codigo_barras",
            "categoria", "fornecedor_principal",
            "unidade_medida", "controla_validade",
            "estoque_minimo", "estoque_ideal",
            "localizacao", "observacoes", "ativo",
        ]
        widgets = {
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilo()
        self.fields["categoria"].queryset = Categoria.objects.filter(ativa=True)
        self.fields["fornecedor_principal"].queryset = Fornecedor.objects.filter(ativo=True)
        self.fields["fornecedor_principal"].empty_label = "— Sem fornecedor principal —"


class ConfiguracaoForm(FormBaseMixin, forms.ModelForm):
    class Meta:
        model = ConfiguracaoSingleton
        fields = [
            "empresa_nome", "empresa_cnpj", "empresa_telefone", "empresa_endereco",
            "alerta_vencimento_30", "alerta_vencimento_15",
            "alerta_vencimento_7", "alerta_vencimento_3",
            "janela_consumo_dias",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilo()


class FiltroProdutoForm(forms.Form):
    busca = forms.CharField(required=False, label="Buscar")
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.filter(ativa=True),
        required=False, empty_label="Todas as categorias",
    )
    ativo = forms.ChoiceField(
        required=False,
        choices=[("", "Todos"), ("True", "Ativos"), ("False", "Inativos")],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            widget.attrs.setdefault("class", ESTILO_CAMPO)
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "rounded border-gray-300 text-emerald-600"


ProdutoEstoqueFormSet = forms.modelformset_factory(
    Produto,
    fields=["estoque_minimo", "estoque_ideal"],
    extra=0,
    widgets={
        "estoque_minimo": forms.NumberInput(attrs={"class": ESTILO_CAMPO, "min": "0", "step": "0.01"}),
        "estoque_ideal": forms.NumberInput(attrs={"class": ESTILO_CAMPO, "min": "0", "step": "0.01"}),
    },
)
