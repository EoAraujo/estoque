"""Views principais: dashboard e cadastros."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, ListView, UpdateView, DetailView,
)

from .forms import (
    CategoriaForm, FornecedorForm, ProdutoForm, ConfiguracaoForm, FiltroProdutoForm,
)
from .models import Categoria, Fornecedor, Produto, ConfiguracaoSingleton


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restringe a usuários ativos com permissão de staff."""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_active

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, "Você não tem permissão para essa ação.")
        return redirect("core:dashboard")


# ============================================================================
# Dashboard
# ============================================================================
def dashboard(request):
    """Dashboard gerencial com KPIs, gráfico de cobertura e ações rápidas."""
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    from datetime import timedelta
    from decimal import Decimal
    from django.utils import timezone

    from accounts.models import UserProfile
    from intelligence.analises import (
        consumo_medio, dias_restantes, data_estimada_ruptura,
        produto_em_excesso, produto_estoque_baixo,
    )
    from stock.models import Lote, Movimento
    from stock.services import valor_total_estoque_produto

    # Período de análise: ?periodo=NN ou profile.periodo_padrao
    periodos_validos = dict(UserProfile.PERIODO_CHOICES)
    raw = request.GET.get("periodo")
    periodo_dias = None
    if raw and raw.isdigit() and int(raw) in periodos_validos:
        periodo_dias = int(raw)
    if periodo_dias is None:
        profile = getattr(request.user, "profile", None)
        periodo_dias = profile.periodo_padrao if profile else UserProfile.PERIODO_PADRAO

    hoje = timezone.localdate()
    desde = timezone.now() - timedelta(days=periodo_dias)

    # ----- KPIs -----
    produtos_ativos = Produto.objects.filter(ativo=True)
    total_produtos = produtos_ativos.count()
    total_categorias = Categoria.objects.filter(ativa=True).count()
    total_fornecedores = Fornecedor.objects.filter(ativo=True).count()

    valor_total_estoque = sum(
        (valor_total_estoque_produto(p) for p in produtos_ativos),
        Decimal("0"),
    )

    lotes_vencendo_qty = Lote.objects.filter(
        ativo=True, quantidade_atual__gt=0,
        data_validade__isnull=False,
        data_validade__gte=hoje,
        data_validade__lte=hoje + timedelta(days=30),
    ).count()
    lotes_vencidos_qty = Lote.objects.filter(
        ativo=True, quantidade_atual__gt=0,
        data_validade__isnull=False, data_validade__lt=hoje,
    ).count()

    # Movs do período
    movs_periodo = Movimento.objects.filter(
        data_movimento__gte=desde, cancelado=False,
    )
    total_entradas_periodo = movs_periodo.filter(tipo="ENTRADA").count()
    total_saidas_periodo = movs_periodo.filter(tipo="SAIDA").count()

    # Últimas movimentações
    ultimas_movs = (
        Movimento.objects
        .select_related("produto", "created_by")
        .order_by("-data_movimento")[:5]
    )

    # Estoque baixo
    produtos_estoque_baixo = [
        p for p in produtos_ativos.select_related("categoria")[:50]
        if produto_estoque_baixo(p)
    ][:6]

    # ----- Gráfico: Dias de cobertura por produto -----
    produtos_cobertura = []
    for p in produtos_ativos.select_related("categoria"):
        consumo = consumo_medio(p)
        qtd = p.quantidade_atual
        if consumo <= 0 or qtd <= 0:
            dias = None
        else:
            dias = float(qtd / consumo)
        produtos_cobertura.append({
            "produto": p,
            "dias": dias,
            "consumo": float(consumo),
            "qtd": float(qtd),
        })
    # Ordena por menor cobertura (mais crítico)
    produtos_cobertura.sort(
        key=lambda x: (x["dias"] is None, x["dias"] if x["dias"] is not None else 0)
    )
    # Mantém top 20 para visualização
    produtos_cobertura_chart = [x for x in produtos_cobertura if x["dias"] is not None][:20]
    # Cor por faixa: 0-7 (vermelho), 8-15 (amarelo), 16-30 (verde), 31+ (azul)
    def cor_por_faixa(d):
        if d <= 7:
            return "#DC2626"  # red-600
        if d <= 15:
            return "#D97706"  # amber-600
        if d <= 30:
            return "#059669"  # emerald-600
        return "#2563EB"      # blue-600
    chart_labels = [x["produto"].nome for x in produtos_cobertura_chart]
    chart_data = [round(x["dias"], 1) for x in produtos_cobertura_chart]
    chart_cores = [cor_por_faixa(x["dias"]) for x in produtos_cobertura_chart]

    # Distribuição por faixa (para mini-KPIs)
    faixas_count = {"critico": 0, "atencao": 0, "normal": 0, "excesso": 0}
    for x in produtos_cobertura:
        if x["dias"] is None:
            continue
        if x["dias"] <= 7:
            faixas_count["critico"] += 1
        elif x["dias"] <= 15:
            faixas_count["atencao"] += 1
        elif x["dias"] <= 30:
            faixas_count["normal"] += 1
        else:
            faixas_count["excesso"] += 1

    context = {
        "total_produtos": total_produtos,
        "total_categorias": total_categorias,
        "total_fornecedores": total_fornecedores,
        "valor_total_estoque": valor_total_estoque,
        "lotes_vencendo_qty": lotes_vencendo_qty,
        "lotes_vencidos_qty": lotes_vencidos_qty,
        "ultimas_movs": ultimas_movs,
        "produtos_estoque_baixo": produtos_estoque_baixo,

        "periodo_dias": periodo_dias,
        "periodo_choices": UserProfile.PERIODO_CHOICES,
        "total_entradas_periodo": total_entradas_periodo,
        "total_saidas_periodo": total_saidas_periodo,

        "produtos_cobertura": produtos_cobertura_chart,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
        "chart_cores": chart_cores,
        "faixas_count": faixas_count,
    }
    return render(request, "dashboard.html", context)


def offline(request):
    """Página de fallback para modo offline (PWA)."""
    return render(request, "offline.html")


# ============================================================================
# Categoria
# ============================================================================
class CategoriaListView(StaffRequiredMixin, ListView):
    model = Categoria
    template_name = "core/categoria_list.html"
    context_object_name = "categorias"
    paginate_by = 25


class CategoriaCreateView(StaffRequiredMixin, CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "core/categoria_form.html"
    success_url = reverse_lazy("core:categoria_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, f"Categoria '{form.instance.nome}' criada com sucesso.")
        return super().form_valid(form)


class CategoriaUpdateView(StaffRequiredMixin, UpdateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "core/categoria_form.html"
    success_url = reverse_lazy("core:categoria_list")

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, f"Categoria '{form.instance.nome}' atualizada.")
        return super().form_valid(form)


class CategoriaDeleteView(StaffRequiredMixin, DeleteView):
    model = Categoria
    template_name = "core/confirmar_exclusao.html"
    success_url = reverse_lazy("core:categoria_list")

    def form_valid(self, form):
        messages.success(self.request, "Categoria removida.")
        return super().form_valid(form)


# ============================================================================
# Fornecedor
# ============================================================================
class FornecedorListView(StaffRequiredMixin, ListView):
    model = Fornecedor
    template_name = "core/fornecedor_list.html"
    context_object_name = "fornecedores"
    paginate_by = 20


class FornecedorCreateView(StaffRequiredMixin, CreateView):
    model = Fornecedor
    form_class = FornecedorForm
    template_name = "core/fornecedor_form.html"
    success_url = reverse_lazy("core:fornecedor_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, f"Fornecedor '{form.instance}' cadastrado.")
        return super().form_valid(form)


class FornecedorUpdateView(StaffRequiredMixin, UpdateView):
    model = Fornecedor
    form_class = FornecedorForm
    template_name = "core/fornecedor_form.html"
    success_url = reverse_lazy("core:fornecedor_list")

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, f"Fornecedor '{form.instance}' atualizado.")
        return super().form_valid(form)


class FornecedorDeleteView(StaffRequiredMixin, DeleteView):
    model = Fornecedor
    template_name = "core/confirmar_exclusao.html"
    success_url = reverse_lazy("core:fornecedor_list")

    def form_valid(self, form):
        messages.success(self.request, "Fornecedor removido.")
        return super().form_valid(form)


# ============================================================================
# Produto
# ============================================================================
class ProdutoListView(StaffRequiredMixin, ListView):
    model = Produto
    template_name = "core/produto_list.html"
    context_object_name = "produtos"
    paginate_by = 30

    def get_queryset(self):
        from decimal import Decimal
        from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Value
        from django.db.models.functions import Coalesce
        # Anota entradas e saídas (excluindo cancelados) e calcula o estoque
        # resultante. ExpressionWrapper garante output_field=DecimalField em
        # todos os backends (PostgreSQL não infere o tipo da subtração).
        decimal_field = DecimalField(max_digits=12, decimal_places=3)
        qs = (
            Produto.objects
            .select_related("categoria", "fornecedor_principal")
            .annotate(
                qtd_estoque=ExpressionWrapper(
                    Coalesce(
                        Sum(
                            "movimentos__quantidade",
                            filter=Q(
                                movimentos__tipo="ENTRADA",
                                movimentos__cancelado=False,
                            ),
                        ),
                        Value(Decimal("0")),
                        output_field=decimal_field,
                    )
                    - Coalesce(
                        Sum(
                            "movimentos__quantidade",
                            filter=Q(
                                movimentos__tipo="SAIDA",
                                movimentos__cancelado=False,
                            ),
                        ),
                        Value(Decimal("0")),
                        output_field=decimal_field,
                    ),
                    output_field=decimal_field,
                ),
            )
        )
        f = FiltroProdutoForm(self.request.GET or None)
        if f.is_valid():
            busca = f.cleaned_data.get("busca")
            categoria = f.cleaned_data.get("categoria")
            ativo = f.cleaned_data.get("ativo")
            if busca:
                qs = qs.filter(
                    Q(nome__icontains=busca) |
                    Q(codigo_interno__icontains=busca) |
                    Q(codigo_barras__icontains=busca)
                )
            if categoria:
                qs = qs.filter(categoria=categoria)
            if ativo in ("True", "False"):
                qs = qs.filter(ativo=ativo == "True")
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filtro_form"] = FiltroProdutoForm(self.request.GET or None)
        return ctx


class ProdutoCreateView(StaffRequiredMixin, CreateView):
    model = Produto
    form_class = ProdutoForm
    template_name = "core/produto_form.html"
    success_url = reverse_lazy("core:produto_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, f"Produto '{form.instance.nome}' criado.")
        return super().form_valid(form)


class ProdutoUpdateView(StaffRequiredMixin, UpdateView):
    model = Produto
    form_class = ProdutoForm
    template_name = "core/produto_form.html"
    success_url = reverse_lazy("core:produto_list")

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, f"Produto '{form.instance.nome}' atualizado.")
        return super().form_valid(form)


class ProdutoDetailView(StaffRequiredMixin, DetailView):
    model = Produto
    template_name = "core/produto_detail.html"
    context_object_name = "produto"

    def get_queryset(self):
        return Produto.objects.select_related("categoria", "fornecedor_principal")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from stock.models import Lote, Movimento
        from stock.services import valor_medio_unitario, valor_total_estoque_produto
        ctx["lotes"] = (
            Lote.objects
            .filter(produto=self.object, ativo=True)
            .order_by("data_validade", "data_entrada")
        )
        ctx["movimentos"] = (
            Movimento.objects
            .filter(produto=self.object)
            .select_related("lote", "created_by")
            .order_by("-data_movimento")[:50]
        )
        ctx["valor_medio"] = valor_medio_unitario(self.object)
        ctx["valor_total"] = valor_total_estoque_produto(self.object)
        return ctx


class ProdutoDeleteView(StaffRequiredMixin, DeleteView):
    model = Produto
    template_name = "core/confirmar_exclusao.html"
    success_url = reverse_lazy("core:produto_list")

    def form_valid(self, form):
        messages.success(self.request, "Produto removido.")
        return super().form_valid(form)


# ============================================================================
# Configurações
# ============================================================================
class ConfiguracaoUpdateView(StaffRequiredMixin, UpdateView):
    model = ConfiguracaoSingleton
    form_class = ConfiguracaoForm
    template_name = "core/configuracao_form.html"
    success_url = reverse_lazy("core:configuracao")

    def get_object(self, queryset=None):
        return ConfiguracaoSingleton.get()

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Configurações atualizadas.")
        return super().form_valid(form)
