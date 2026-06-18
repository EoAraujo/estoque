"""Views de autenticação e gestão de usuários."""
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from .forms import (
    LoginFormEstilizado, RedefinirSenhaForm, UsuarioForm, UsuarioUpdateForm,
)
from .models import UserProfile

User = get_user_model()


# ============================================================================
# Autenticação
# ============================================================================
def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    form = LoginFormEstilizado(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f"Bem-vindo(a), {user.first_name or user.username}!")
        return redirect("core:dashboard")
    return render(request, "registration/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Você saiu do sistema.")
    return redirect("accounts:login")


# ============================================================================
# Gestão de usuários
# ============================================================================
class StaffObrigatorioMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_active

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, "Você não tem permissão para essa ação.")
        return redirect("core:dashboard")


class UsuarioListView(StaffObrigatorioMixin, ListView):
    template_name = "accounts/usuario_list.html"
    context_object_name = "usuarios"
    paginate_by = 25

    def get_queryset(self):
        return User.objects.select_related("profile").order_by("username")


class UsuarioCreateView(StaffObrigatorioMixin, CreateView):
    form_class = UsuarioForm
    template_name = "accounts/usuario_form.html"
    success_url = reverse_lazy("accounts:usuario_list")

    def form_valid(self, form):
        messages.success(self.request, f"Usuário '{form.instance.username}' criado.")
        return super().form_valid(form)


class UsuarioUpdateView(StaffObrigatorioMixin, UpdateView):
    model = User
    form_class = UsuarioUpdateForm
    template_name = "accounts/usuario_form.html"
    success_url = reverse_lazy("accounts:usuario_list")
    context_object_name = "obj"

    def form_valid(self, form):
        messages.success(self.request, f"Usuário '{form.instance.username}' atualizado.")
        return super().form_valid(form)


@login_required
def redefinir_senha(request, pk):
    """Permite a um staff redefinir a senha de outro usuário."""
    if not request.user.is_staff:
        messages.error(request, "Sem permissão.")
        return redirect("core:dashboard")
    user = get_object_or_404(User, pk=pk)
    form = RedefinirSenhaForm(user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Senha de '{user.username}' redefinida.")
        return redirect("accounts:usuario_list")
    return render(request, "accounts/redefinir_senha.html", {
        "form": form, "obj": user,
    })


@login_required
def toggle_ativo(request, pk):
    """Ativa/inativa um usuário."""
    if not request.user.is_staff:
        messages.error(request, "Sem permissão.")
        return redirect("core:dashboard")
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.warning(request, "Você não pode inativar o seu próprio usuário.")
        return redirect("accounts:usuario_list")
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    estado = "ativado" if user.is_active else "inativado"
    messages.success(request, f"Usuário '{user.username}' {estado}.")
    return redirect("accounts:usuario_list")


@login_required
def minhas_preferencias(request):
    """Edita o período padrão do usuário logado."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        novo = request.POST.get("periodo_padrao")
        if novo and novo.isdigit() and int(novo) in dict(UserProfile.PERIODO_CHOICES):
            profile.periodo_padrao = int(novo)
            profile.save()
            messages.success(request, "Período padrão atualizado.")
            return redirect("core:dashboard")
        messages.error(request, "Período inválido.")
    return render(request, "accounts/preferencias.html", {"profile": profile})
