from django.contrib import admin
from .models import Lote, Movimento, Alerta


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ("produto", "numero_lote", "data_validade", "quantidade_atual", "ativo")
    list_filter = ("ativo", "data_validade")
    search_fields = ("produto__nome", "numero_lote", "nota_fiscal")
    autocomplete_fields = ("produto",)
    date_hierarchy = "data_validade"


@admin.register(Movimento)
class MovimentoAdmin(admin.ModelAdmin):
    list_display = ("data_movimento", "tipo", "produto", "quantidade", "motivo", "cancelado")
    list_filter = ("tipo", "motivo", "cancelado")
    search_fields = ("produto__nome", "nota_fiscal", "responsavel")
    autocomplete_fields = ("produto", "lote", "fornecedor")
    date_hierarchy = "data_movimento"
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")

    def has_delete_permission(self, request, obj=None):
        # Movimentos NUNCA são apagados; usa-se cancelamento.
        return False


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ("created_at", "nivel", "tipo", "titulo", "lido", "resolvido")
    list_filter = ("nivel", "tipo", "lido", "resolvido")
    search_fields = ("titulo", "mensagem", "produto__nome")
    readonly_fields = ("created_at", "updated_at")
