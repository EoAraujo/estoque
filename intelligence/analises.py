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
    """
    Percorre produtos ativos e gera Alerta quando necessário.
    Retorna quantidade de alertas criados.
    """
    from stock.models import Alerta
    from datetime import timedelta

    config = ConfiguracaoSingleton.get()
    hoje = timezone.localdate()
    criados = 0

    produtos = Produto.objects.filter(ativo=True).select_related("categoria")

    for p in produtos:
        # --- Estoque baixo ---
        if p.estoque_minimo and p.estoque_minimo > 0:
            if p.quantidade_atual <= p.estoque_minimo:
                nivel = "CRITICO" if p.quantidade_atual <= 0 else "URGENTE"
                existe = Alerta.objects.filter(
                    produto=p, tipo="ESTOQUE_MIN", resolvido=False
                ).exists()
                if not existe:
                    Alerta.objects.create(
                        tipo="ESTOQUE_MIN",
                        nivel=nivel,
                        produto=p,
                        titulo=f"Estoque baixo: {p.nome}",
                        mensagem=f"Estoque atual: {p.quantidade_atual} {p.unidade_medida} (mínimo: {p.estoque_minimo})",
                        dados={"quantidade_atual": float(p.quantidade_atual), "estoque_minimo": float(p.estoque_minimo)},
                    )
                    criados += 1

        # --- Esgotado ---
        if p.quantidade_atual <= 0:
            existe = Alerta.objects.filter(
                produto=p, tipo="ESGOTADO", resolvido=False
            ).exists()
            if not existe:
                Alerta.objects.create(
                    tipo="ESGOTADO",
                    nivel="CRITICO",
                    produto=p,
                    titulo=f"Esgotado: {p.nome}",
                    mensagem=f"Produto sem estoque. Unidade: {p.unidade_medida}",
                )
                criados += 1

        # --- Ruptura iminente ---
        dias = dias_restantes(p)
        if dias is not None and dias <= config.alerta_vencimento_30:
            nivel = "CRITICO" if dias <= 3 else "URGENTE" if dias <= 7 else "ATENCAO"
            existe = Alerta.objects.filter(
                produto=p, tipo="RUPTURA", resolvido=False
            ).exists()
            if not existe:
                Alerta.objects.create(
                    tipo="RUPTURA",
                    nivel=nivel,
                    produto=p,
                    titulo=f"Ruptura em {int(dias)} dias: {p.nome}",
                    mensagem=f"Estoque atual: {p.quantidade_atual} {p.unidade_medida}. Consumo médio: {consumo_medio(p):.2f}/dia",
                    dados={"dias_restantes": float(dias)},
                )
                criados += 1

        # --- Excesso ---
        if produto_em_excesso(p):
            existe = Alerta.objects.filter(
                produto=p, tipo="EXCESSO", resolvido=False
            ).exists()
            if not existe:
                excedente = p.quantidade_atual - (p.estoque_ideal or 0)
                Alerta.objects.create(
                    tipo="EXCESSO",
                    nivel="INFO",
                    produto=p,
                    titulo=f"Excesso: {p.nome}",
                    mensagem=f"Estoque: {p.quantidade_atual} {p.unidade_medida} (ideal: {p.estoque_ideal}). Excedente: {excedente}",
                    dados={"excedente": float(excedente)},
                )
                criados += 1

        # --- Lotes vencendo ---
        from stock.models import Lote
        lotes_vencendo = Lote.objects.filter(
            produto=p, ativo=True, quantidade_atual__gt=0,
            data_validade__isnull=False,
            data_validade__gte=hoje,
            data_validade__lte=hoje + timedelta(days=config.alerta_vencimento_30),
        )
        for lote in lotes_vencendo:
            dias_v = (lote.data_validade - hoje).days
            tipo_v = (
                "VENCIDO" if dias_v < 0 else
                "VENCIMENTO_3" if dias_v <= 3 else
                "VENCIMENTO_7" if dias_v <= 7 else
                "VENCIMENTO_15" if dias_v <= 15 else
                "VENCIMENTO_30"
            )
            nivel_v = "CRITICO" if dias_v <= 3 else "URGENTE" if dias_v <= 7 else "ATENCAO"
            existe = Alerta.objects.filter(
                produto=p, lote=lote, tipo=tipo_v, resolvido=False
            ).exists()
            if not existe:
                Alerta.objects.create(
                    tipo=tipo_v,
                    nivel=nivel_v,
                    produto=p,
                    lote=lote,
                    titulo=f"Lote vencendo: {p.nome}",
                    mensagem=f"Lote {lote.numero_lote or 's/n'} vence em {lote.data_validade.strftime('%d/%m/%Y')} ({dias_v} dias). Qtd: {lote.quantidade_atual}",
                    dados={"lote_id": lote.pk, "dias_para_vencer": dias_v},
                )
                criados += 1

    return criados
