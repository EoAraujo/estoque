"""Views do módulo de inteligência (Fase 3).

Renderiza a página única de inteligência com seções de:
- KPIs de saúde do estoque
- Ruptura iminente
- Estoque abaixo do mínimo
- Sugestões de compra
- Excesso de estoque
- Anomalias de consumo
"""
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from core.models import ConfiguracaoSingleton, Produto
from stock.services import valor_medio_unitario

from .analises import (
    consumo_medio,
    data_estimada_ruptura,
    dias_restantes,
    produto_em_excesso,
    produto_estoque_baixo,
    quantidade_recomendada_compra,
)


def _calcular_sugestoes(produtos):
    """Gera lista [(produto, qtd_sugerida, valor_estimado)] ordenadas por urgência."""
    sugestoes = []
    for p in produtos:
        qtd = quantidade_recomendada_compra(p)
        if qtd > 0:
            vlr_unit = valor_medio_unitario(p) or Decimal("0")
            valor = (qtd * vlr_unit).quantize(Decimal("0.01"))
            sugestoes.append((p, qtd, valor))
    # Ordena por menor cobertura (mais urgente = estoque mais baixo relativo ao ideal)
    sugestoes.sort(
        key=lambda t: float(t[0].quantidade_atual) / float(t[0].estoque_ideal or 1)
    )
    return sugestoes


def _calcular_rupturas(produtos, janela_dias):
    """Gera lista [(produto, dias_restantes, data_ruptura)] para produtos com risco de ruptura."""
    rupturas = []
    for p in produtos:
        dias = dias_restantes(p)
        if dias is None:
            continue
        if dias > janela_dias:
            continue
        rupturas.append((p, dias, data_estimada_ruptura(p)))
    # Mais urgente primeiro (menor número de dias)
    rupturas.sort(key=lambda t: t[1])
    return rupturas


def _calcular_estoque_baixo(produtos):
    return [p for p in produtos if produto_estoque_baixo(p)]


def _calcular_excesso(produtos):
    """Gera lista [(produto, excedente)] para produtos com estoque acima de 120% do ideal."""
    excessos = []
    for p in produtos:
        if not produto_em_excesso(p):
            continue
        excedente = (p.quantidade_atual - p.estoque_ideal).quantize(Decimal("0.001"))
        excessos.append((p, excedente))
    excessos.sort(key=lambda t: -t[1])
    return excessos


def _calcular_anomalias(produtos, janela_alerta_dias=7):
    """Produtos com consumo acelerado: estoque zera em <= janela_alerta_dias."""
    anomalias = []
    for p in produtos:
        dias = dias_restantes(p)
        if dias is None or dias <= 0:
            continue
        if dias > janela_alerta_dias:
            continue
        if p.quantidade_atual <= 0:
            continue
        anomalias.append((p, dias, consumo_medio(p)))
    anomalias.sort(key=lambda t: t[1])
    return anomalias


@login_required
def intelligence_home(request):
    """Página única de inteligência de estoque."""
    config = ConfiguracaoSingleton.get()
    hoje = timezone.localdate()

    produtos = list(
        Produto.objects
        .filter(ativo=True)
        .select_related("categoria", "fornecedor_principal")
    )

    rupturas = _calcular_rupturas(produtos, janela_dias=config.alerta_vencimento_30)
    estoque_baixo = _calcular_estoque_baixo(produtos)
    sugestoes = _calcular_sugestoes(produtos)
    excessos = _calcular_excesso(produtos)
    anomalias = _calcular_anomalias(produtos, janela_alerta_dias=7)

    valor_total_sugestoes = sum(
        (valor for _, _, valor in sugestoes), Decimal("0")
    )
    valor_total_excesso = sum(
        (
            (p.quantidade_atual * (valor_medio_unitario(p) or Decimal("0")))
            for p, _ in excessos
        ),
        Decimal("0"),
    )

    context = {
        "hoje": hoje,
        "config": config,
        "janela_consumo": config.janela_consumo_dias,
        "total_produtos_ativos": len(produtos),

        "rupturas": rupturas,
        "rupturas_count": len(rupturas),

        "estoque_baixo": estoque_baixo,
        "estoque_baixo_count": len(estoque_baixo),

        "sugestoes": sugestoes,
        "sugestoes_count": len(sugestoes),
        "valor_total_sugestoes": valor_total_sugestoes,

        "excessos": excessos,
        "excessos_count": len(excessos),
        "valor_total_excesso": valor_total_excesso,

        "anomalias": anomalias,
        "anomalias_count": len(anomalias),
    }
    return render(request, "intelligence/home.html", context)


@login_required
def api_alertas(request):
    """API: retorna alertas ativos (não lidos, não resolvidos) para o header."""
    from stock.models import Alerta

    alertas = (
        Alerta.objects
        .filter(resolvido=False)
        .select_related("produto", "lote")
        .order_by("-created_at")[:30]
    )

    data = []
    for a in alertas:
        data.append({
            "id": a.pk,
            "tipo": a.tipo,
            "nivel": a.nivel,
            "titulo": a.titulo,
            "mensagem": a.mensagem,
            "tipo_display": a.get_tipo_display(),
            "nivel_display": a.get_nivel_display(),
            "produto": a.produto.nome if a.produto else None,
            "lote": str(a.lote) if a.lote else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })

    return JsonResponse({"alertas": data, "total": len(data)})


@login_required
def api_gerar_alertas(request):
    """API: dispara geração de alertas. Retorna quantidade criada."""
    from .analises import gerar_alertas
    criados = gerar_alertas()
    return JsonResponse({"criados": criados})
