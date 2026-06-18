"""Views do módulo de estoque (Fase 2)."""
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView

from core.models import Produto

from .forms import (
    AjusteForm, CancelarMovimentoForm, EntradaForm, FiltroMovimentoForm,
    SaidaForm,
)
from .models import Lote, Movimento
from .services import (
    EstoqueError, cancelar_movimento, registrar_ajuste, registrar_entrada,
    registrar_saida, valor_medio_unitario, valor_total_estoque_produto,
)


class StaffRequired(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_active


# ============================================================================
# Dashboard
# ============================================================================
@login_required
def stock_dashboard(request):
    """Visão geral de movimentações."""
    ultimas = (
        Movimento.objects
        .select_related("produto", "lote", "fornecedor", "created_by")
        .order_by("-data_movimento")[:10]
    )

    hoje = timezone.localdate()
    inicio_dia = timezone.make_aware(timezone.datetime.combine(hoje, timezone.datetime.min.time()))

    saidas_hoje = (
        Movimento.objects
        .filter(tipo="SAIDA", cancelado=False, data_movimento__gte=inicio_dia)
        .aggregate(s=Sum("quantidade"))["s"] or Decimal("0")
    )
    entradas_hoje = (
        Movimento.objects
        .filter(tipo="ENTRADA", cancelado=False, data_movimento__gte=inicio_dia)
        .aggregate(s=Sum("quantidade"))["s"] or Decimal("0")
    )
    cancelamentos_30d = Movimento.objects.filter(
        cancelado=True,
        data_movimento__gte=timezone.now() - timedelta(days=30),
    ).count()

    # Lotes vencendo nos próximos 30 dias
    lotes_vencendo = (
        Lote.objects
        .filter(
            ativo=True, quantidade_atual__gt=0,
            data_validade__isnull=False,
            data_validade__gte=hoje,
            data_validade__lte=hoje + timedelta(days=30),
        )
        .select_related("produto")
        .order_by("data_validade")[:10]
    )
    lotes_vencidos = (
        Lote.objects
        .filter(
            ativo=True, quantidade_atual__gt=0,
            data_validade__isnull=False, data_validade__lt=hoje,
        )
        .select_related("produto")
        .order_by("data_validade")[:10]
    )

    # Valor total em estoque
    produtos_ativos = Produto.objects.filter(ativo=True)
    valor_total_estoque = sum(
        (valor_total_estoque_produto(p) for p in produtos_ativos),
        Decimal("0")
    )

    # Top produtos por valor em estoque
    top_produtos = sorted(
        (
            (p, valor_total_estoque_produto(p))
            for p in produtos_ativos
        ),
        key=lambda x: x[1], reverse=True
    )[:5]

    context = {
        "ultimas": ultimas,
        "saidas_hoje": saidas_hoje,
        "entradas_hoje": entradas_hoje,
        "cancelamentos_30d": cancelamentos_30d,
        "lotes_vencendo": lotes_vencendo,
        "lotes_vencidos": lotes_vencidos,
        "valor_total_estoque": valor_total_estoque,
        "top_produtos": top_produtos,
    }
    return render(request, "stock/dashboard.html", context)


# ============================================================================
# Movimentação - helpers
# ============================================================================
def _produtos_estoque_choices():
    return Produto.objects.filter(ativo=True).select_related("categoria").order_by("nome")


# ============================================================================
# Entrada
# ============================================================================
class EntradaCreateView(StaffRequired, CreateView):
    form_class = EntradaForm
    template_name = "stock/entrada_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Registrar entrada de estoque"
        ctx["tipo"] = "ENTRADA"
        return ctx

    def get_initial(self):
        initial = super().get_initial()
        produto_id = self.request.GET.get("produto")
        if produto_id:
            try:
                initial["produto"] = Produto.objects.get(pk=int(produto_id), ativo=True)
            except (Produto.DoesNotExist, ValueError):
                pass
        return initial

    def form_valid(self, form):
        try:
            movimento = registrar_entrada(
                produto=form.cleaned_data["produto"],
                quantidade=form.cleaned_data["quantidade"],
                data_entrada=form.cleaned_data["data_entrada"],
                numero_lote=form.cleaned_data.get("numero_lote", ""),
                data_fabricacao=form.cleaned_data.get("data_fabricacao"),
                data_validade=form.cleaned_data.get("data_validade"),
                valor_unitario=form.cleaned_data.get("valor_unitario"),
                fornecedor=form.cleaned_data.get("fornecedor"),
                nota_fiscal=form.cleaned_data.get("nota_fiscal", ""),
                observacoes=form.cleaned_data.get("observacoes", ""),
                motivo=form.cleaned_data.get("motivo", "COMPRA"),
                usuario=self.request.user,
            )
        except EstoqueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        messages.success(
            self.request,
            f"Entrada registrada: +{movimento.quantidade} {movimento.produto.unidade_medida} "
            f"de '{movimento.produto.nome}'."
        )
        return redirect("stock:movimento_detail", pk=movimento.pk)


# ============================================================================
# Saída
# ============================================================================
class SaidaCreateView(StaffRequired, CreateView):
    form_class = SaidaForm
    template_name = "stock/saida_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Registrar saída de estoque"
        ctx["tipo"] = "SAIDA"
        return ctx

    def get_initial(self):
        initial = super().get_initial()
        produto_id = self.request.GET.get("produto")
        if produto_id:
            try:
                initial["produto"] = Produto.objects.get(pk=int(produto_id), ativo=True)
            except (Produto.DoesNotExist, ValueError):
                pass
        return initial

    def form_valid(self, form):
        try:
            resultado = registrar_saida(
                produto=form.cleaned_data["produto"],
                quantidade=form.cleaned_data["quantidade"],
                motivo=form.cleaned_data.get("motivo", "PRODUCAO"),
                responsavel=form.cleaned_data.get("responsavel", ""),
                observacoes=form.cleaned_data.get("observacoes", ""),
                lote=form.cleaned_data.get("lote"),
                usuario=self.request.user,
            )
        except EstoqueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        if isinstance(resultado, list):
            messages.success(self.request,
                f"Saída registrada em {len(resultado)} lote(s): "
                f"-{form.cleaned_data['quantidade']} {form.cleaned_data['produto'].unidade_medida} "
                f"de '{form.cleaned_data['produto'].nome}'."
            )
            return redirect("stock:movimento_list")
        messages.success(self.request,
            f"Saída registrada: -{resultado.quantidade} {resultado.produto.unidade_medida} "
            f"de '{resultado.produto.nome}'."
        )
        return redirect("stock:movimento_detail", pk=resultado.pk)


# ============================================================================
# Ajuste
# ============================================================================
class AjusteCreateView(StaffRequired, CreateView):
    form_class = AjusteForm
    template_name = "stock/ajuste_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Ajuste manual de inventário"
        return ctx

    def get_initial(self):
        initial = super().get_initial()
        produto_id = self.request.GET.get("produto")
        if produto_id:
            try:
                initial["produto"] = Produto.objects.get(pk=int(produto_id), ativo=True)
            except (Produto.DoesNotExist, ValueError):
                pass
        return initial

    def form_valid(self, form):
        try:
            movimento = registrar_ajuste(
                produto=form.cleaned_data["produto"],
                quantidade=form.cleaned_data["quantidade"],
                direcao=form.cleaned_data["direcao"],
                motivo_detalhado=dict(form.fields["motivo"].choices)
                    .get(form.cleaned_data["motivo"], ""),
                observacoes=form.cleaned_data["observacoes"],
                lote=form.cleaned_data.get("lote"),
                usuario=self.request.user,
            )
        except EstoqueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        sinal = "+" if movimento.tipo == "ENTRADA" else "-"
        messages.success(self.request,
            f"Ajuste registrado: {sinal}{movimento.quantidade} "
            f"{movimento.produto.unidade_medida} de '{movimento.produto.nome}'."
        )
        return redirect("stock:movimento_detail", pk=movimento.pk)


# ============================================================================
# Listagem
# ============================================================================
@login_required
def movimento_list(request):
    form = FiltroMovimentoForm(request.GET or None)
    qs = (
        Movimento.objects
        .select_related("produto", "lote", "fornecedor", "created_by")
        .all()
    )
    if form.is_valid():
        busca = form.cleaned_data.get("busca")
        tipo = form.cleaned_data.get("tipo")
        produto = form.cleaned_data.get("produto")
        data_inicio = form.cleaned_data.get("data_inicio")
        data_fim = form.cleaned_data.get("data_fim")
        cancelado = form.cleaned_data.get("cancelado")
        if busca:
            qs = qs.filter(
                Q(observacoes__icontains=busca) |
                Q(nota_fiscal__icontains=busca) |
                Q(produto__nome__icontains=busca) |
                Q(produto__codigo_interno__icontains=busca) |
                Q(responsavel__icontains=busca)
            )
        if tipo:
            qs = qs.filter(tipo=tipo)
        if produto:
            qs = qs.filter(produto=produto)
        if data_inicio:
            qs = qs.filter(data_movimento__date__gte=data_inicio)
        if data_fim:
            qs = qs.filter(data_movimento__date__lte=data_fim)
        if cancelado in ("True", "False"):
            qs = qs.filter(cancelado=(cancelado == "True"))

    paginator = Paginator(qs, 30)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "stock/movimento_list.html", {
        "page": page,
        "form": form,
        "total_resultados": qs.count(),
    })


# ============================================================================
# Detalhe + cancelamento
# ============================================================================
@login_required
def movimento_detail(request, pk):
    movimento = get_object_or_404(
        Movimento.objects.select_related("produto", "lote", "fornecedor", "created_by", "updated_by"),
        pk=pk,
    )
    # Movimentos relacionados (quando saída usou FEFO, vários com mesmo "lote pai")
    relacionados = []
    if movimento.observacoes and movimento.tipo == "SAIDA":
        relacionados = []
    return render(request, "stock/movimento_detail.html", {
        "m": movimento,
    })


@login_required
def movimento_cancelar(request, pk):
    movimento = get_object_or_404(Movimento, pk=pk)
    if movimento.cancelado:
        messages.info(request, "Este movimento já está cancelado.")
        return redirect("stock:movimento_detail", pk=pk)

    if not request.user.is_staff:
        messages.error(request, "Sem permissão para cancelar movimentos.")
        return redirect("stock:movimento_detail", pk=pk)

    form = CancelarMovimentoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            cancelar_movimento(
                movimento,
                motivo_cancelamento=form.cleaned_data["motivo_cancelamento"],
                usuario=request.user,
            )
        except EstoqueError as e:
            messages.error(request, str(e))
            return redirect("stock:movimento_detail", pk=pk)
        messages.success(
            request,
            f"Movimento cancelado. Estoque revertido."
        )
        return redirect("stock:movimento_detail", pk=pk)

    return render(request, "stock/movimento_cancelar.html", {
        "m": movimento, "form": form,
    })
