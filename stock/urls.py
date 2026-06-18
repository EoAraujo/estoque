"""URLs do módulo de estoque."""
from django.urls import path

from . import views

app_name = "stock"

urlpatterns = [
    path("", views.stock_dashboard, name="home"),

    path("movimentacoes/", views.movimento_list, name="movimento_list"),
    path("movimentacoes/<int:pk>/", views.movimento_detail, name="movimento_detail"),
    path("movimentacoes/<int:pk>/cancelar/", views.movimento_cancelar, name="movimento_cancelar"),

    path("entradas/nova/", views.EntradaCreateView.as_view(), name="entrada_create"),
    path("saidas/nova/", views.SaidaCreateView.as_view(), name="saida_create"),
    path("ajustes/novo/", views.AjusteCreateView.as_view(), name="ajuste_create"),
]
