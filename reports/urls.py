from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("movimentacoes.xlsx", views.exportar_movimentacoes_xlsx, name="movimentacoes_xlsx"),
    path("estoque.xlsx", views.exportar_posicao_estoque_xlsx, name="estoque_xlsx"),
    path("auditoria.xlsx", views.exportar_auditoria_xlsx, name="auditoria_xlsx"),
    path("validade.pdf", views.exportar_validade_pdf, name="validade_pdf"),
]
