from django.urls import path
from . import views

app_name = "intelligence"

urlpatterns = [
    path("", views.intelligence_home, name="home"),
    path("api/alertas/", views.api_alertas, name="api_alertas"),
    path("api/gerar-alertas/", views.api_gerar_alertas, name="api_gerar_alertas"),
]
