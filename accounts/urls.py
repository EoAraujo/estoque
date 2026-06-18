from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("usuarios/", views.UsuarioListView.as_view(), name="usuario_list"),
    path("usuarios/novo/", views.UsuarioCreateView.as_view(), name="usuario_create"),
    path("usuarios/<int:pk>/editar/", views.UsuarioUpdateView.as_view(), name="usuario_update"),
    path("usuarios/<int:pk>/senha/", views.redefinir_senha, name="redefinir_senha"),
    path("usuarios/<int:pk>/toggle/", views.toggle_ativo, name="toggle_ativo"),
    path("preferencias/", views.minhas_preferencias, name="preferencias"),
]
