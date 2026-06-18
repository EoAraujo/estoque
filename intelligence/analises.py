"""
Motor de inteligência de estoque.

Cálculos de consumo, previsão, ruptura, validade, excesso, etc.
Implementação prevista para a Fase 2 do projeto.
"""
from decimal import Decimal
from datetime import timedelta

from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncDate
from django.utils import timezone

from core.models import Produto, ConfiguracaoSingleton
from stock.models import Lote, Movimento


def consumo_medio(produto: Produto, dias: int = None) -> Decimal:
    """
    Retorna o consumo médio diário do produto nos últimos `dias` dias,
    considerando apenas movimentações de saída ativas.
    """
    if dias is None:
        dias = ConfiguracaoSingleton.get().janela_consumo_dias

    desde = timezone.now() - timedelta(days=dias)
    total = (
        Movimento.objects
        .filter(
            produto=produto, tipo="SAIDA", cancelado=False,
            data_movimento__gte=desde,
        )
        .aggregate(s=Sum("quantidade"))["s"]
    ) or Decimal("0")
    return (total / Decimal(dias)) if dias else Decimal("0")


def dias_restantes(produto: Produto) -> Decimal:
    """Quantos dias o estoque atual deve durar dado o consumo médio."""
    consumo = consumo_medio(produto)
    if consumo <= 0:
        return None  # Sem histórico de consumo
    return (produto.quantidade_atual / consumo).quantize(Decimal("0.1"))


def data_estimada_ruptura(produto: Produto):
    """Data em que o estoque zera, considerando consumo médio."""
    dias = dias_restantes(produto)
    if dias is None:
        return None
    return timezone.localdate() + timedelta(days=int(dias))


def produto_em_excesso(produto: Produto) -> bool:
    """Retorna True se o estoque atual ultrapassa o ideal em mais de 20%."""
    if not produto.estoque_ideal or produto.estoque_ideal <= 0:
        return False
    return produto.quantidade_atual > (produto.estoque_ideal * Decimal("1.2"))


def produto_estoque_baixo(produto: Produto) -> bool:
    """Retorna True se o estoque atual está abaixo do mínimo."""
    if not produto.estoque_minimo or produto.estoque_minimo <= 0:
        return False
    return produto.quantidade_atual <= produto.estoque_minimo


def quantidade_recomendada_compra(produto: Produto) -> Decimal:
    """Sugere a quantidade a comprar para atingir o estoque ideal."""
    if not produto.estoque_ideal or produto.estoque_ideal <= 0:
        return Decimal("0")
    falta = produto.estoque_ideal - produto.quantidade_atual
    return max(falta, Decimal("0"))


# Implementação completa em Fase 2
def gerar_alertas():
    """Percorre produtos/lotes e gera alertas."""
    raise NotImplementedError("Motor de alertas será implementado na Fase 2.")
