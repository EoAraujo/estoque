from django.contrib import admin
from .models import LogAuditoria


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "usuario", "acao", "modelo", "objeto_repr")
    list_filter = ("acao", "modelo", "timestamp")
    search_fields = ("usuario__username", "objeto_repr", "objeto_id", "url")
    date_hierarchy = "timestamp"
    readonly_fields = (
        "usuario", "acao", "modelo", "objeto_id", "objeto_repr",
        "dados_anteriores", "dados_novos", "ip", "user_agent", "url", "timestamp",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
