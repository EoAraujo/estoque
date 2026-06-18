from django.contrib import admin
from .models import Categoria, Fornecedor, Produto, ConfiguracaoSingleton


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativa", "created_at")
    list_filter = ("ativa",)
    search_fields = ("nome",)
    ordering = ("nome",)


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ("nome", "cnpj", "telefone", "lead_time_days", "ativo")
    list_filter = ("ativo", "estado")
    search_fields = ("nome", "nome_fantasia", "cnpj")
    ordering = ("nome",)


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_interno", "nome", "categoria", "unidade_medida",
        "estoque_minimo", "estoque_ideal", "ativo",
    )
    list_filter = ("ativo", "categoria", "unidade_medida", "controla_validade")
    search_fields = ("nome", "codigo_interno", "codigo_barras")
    autocomplete_fields = ("categoria", "fornecedor_principal")
    ordering = ("nome",)


@admin.register(ConfiguracaoSingleton)
class ConfiguracaoAdmin(admin.ModelAdmin):
    list_display = ("empresa_nome",)

    def has_add_permission(self, request):
        return not ConfiguracaoSingleton.objects.exists()
