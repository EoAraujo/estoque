"""
Serviços de estoque: regras de negócio para movimentações.

Centraliza toda a lógica que altera saldos. As views e o
admin devem chamar estas funções, nunca modificar `quantidade_atual`
diretamente.
"""
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import Sum, F, Q
from django.utils import timezone

from core.models import Produto
from .models import Lote, Movimento


class EstoqueError(Exception):
    """Erro de regra de negócio de estoque."""


# ============================================================================
# 1) Valor médio e custo
# ============================================================================
def valor_medio_unitario(produto: Produto) -> Decimal:
    """
    Calcula o valor unitário médio ponderado do produto com base
    nas últimas entradas (até 90 dias). Retorna Decimal('0') se
    não houver histórico.
    """
    desde = timezone.now() - timezone.timedelta(days=90)
    entradas = (
        Movimento.objects
        .filter(
            produto=produto, tipo="ENTRADA", cancelado=False,
            valor_unitario__isnull=False,
            data_movimento__gte=desde,
        )
        .aggregate(
            total_qtd=Sum("quantidade"),
            total_valor=Sum(F("valor_unitario") * F("quantidade")),
        )
    )
    qtd = entradas["total_qtd"] or Decimal("0")
    valor = entradas["total_valor"] or Decimal("0")
    if qtd <= 0:
        return Decimal("0")
    return (valor / qtd).quantize(Decimal("0.0001"))


def valor_total_estoque_produto(produto: Produto) -> Decimal:
    """Valor total estimado em estoque do produto (qtd atual × valor médio)."""
    qtd = produto.quantidade_atual
    if qtd <= 0:
        return Decimal("0")
    return (qtd * valor_medio_unitario(produto)).quantize(Decimal("0.01"))


# ============================================================================
# 2) Entrada
# ============================================================================
@transaction.atomic
def registrar_entrada(
    *,
    produto: Produto,
    quantidade: Decimal,
    data_entrada,
    numero_lote: str = "",
    data_fabricacao=None,
    data_validade=None,
    valor_unitario: Optional[Decimal] = None,
    fornecedor=None,
    nota_fiscal: str = "",
    observacoes: str = "",
    motivo: str = "COMPRA",
    usuario=None,
) -> Movimento:
    """
    Cria um novo lote (se aplicável) e registra movimento de entrada.
    """
    if quantidade <= 0:
        raise EstoqueError("A quantidade deve ser maior que zero.")

    if produto.controla_validade and not data_validade:
        raise EstoqueError(
            f"O produto '{produto.nome}' exige data de validade. "
            "Informe a validade do lote."
        )

    lote = None
    if produto.controla_validade or numero_lote:
        lote = Lote.objects.create(
            produto=produto,
            numero_lote=numero_lote,
            data_fabricacao=data_fabricacao,
            data_validade=data_validade,
            data_entrada=data_entrada,
            quantidade_inicial=quantidade,
            quantidade_atual=quantidade,
            nota_fiscal=nota_fiscal,
            observacoes=observacoes,
            created_by=usuario,
            updated_by=usuario,
        )

    movimento = Movimento.objects.create(
        produto=produto,
        lote=lote,
        tipo="ENTRADA",
        motivo=motivo,
        quantidade=quantidade,
        valor_unitario=valor_unitario,
        valor_total=(valor_unitario * quantidade) if valor_unitario else None,
        fornecedor=fornecedor,
        nota_fiscal=nota_fiscal,
        data_movimento=timezone.now(),
        observacoes=observacoes,
        created_by=usuario,
        updated_by=usuario,
    )
    return movimento


# ============================================================================
# 3) Saída
# ============================================================================
@transaction.atomic
def registrar_saida(
    *,
    produto: Produto,
    quantidade: Decimal,
    motivo: str,
    responsavel: str = "",
    observacoes: str = "",
    lote: Optional[Lote] = None,
    usuario=None,
) -> Movimento:
    """
    Registra saída consumindo do(s) lote(s) disponível(is).

    Estratégia padrão: FEFO (consome primeiro o lote que vence mais cedo).
    Se um lote for informado explicitamente, consome dele.
    Retorna o movimento criado (ou uma lista se houve rateio entre lotes).
    """
    if quantidade <= 0:
        raise EstoqueError("A quantidade deve ser maior que zero.")

    if produto.quantidade_atual < quantidade:
        raise EstoqueError(
            f"Estoque insuficiente para o produto '{produto.nome}'. "
            f"Disponível: {produto.quantidade_atual} {produto.unidade_medida}."
        )

    restante = quantidade
    movimentos = []

    if lote is not None:
        # Saída direcionada a um lote específico
        if lote.quantidade_atual < restante:
            raise EstoqueError(
                f"Quantidade insuficiente no lote {lote}. "
                f"Disponível: {lote.quantidade_atual} {produto.unidade_medida}."
            )
        lote.quantidade_atual -= restante
        lote.updated_by = usuario
        lote.save(update_fields=["quantidade_atual", "updated_at", "updated_by"])
        restante = Decimal("0")

    if restante > 0:
        # FEFO: consome dos lotes com validade mais próxima
        lotes = list(
            Lote.objects
            .select_for_update()
            .filter(produto=produto, ativo=True, quantidade_atual__gt=0)
            .order_by("data_validade", "data_entrada")
        )
        for l in lotes:
            if restante <= 0:
                break
            consumir = min(l.quantidade_atual, restante)
            l.quantidade_atual -= consumir
            l.updated_by = usuario
            l.save(update_fields=["quantidade_atual", "updated_at", "updated_by"])
            restante -= consumir
            m = Movimento.objects.create(
                produto=produto, lote=l, tipo="SAIDA", motivo=motivo,
                quantidade=consumir, responsavel=responsavel,
                data_movimento=timezone.now(),
                observacoes=observacoes,
                created_by=usuario, updated_by=usuario,
            )
            movimentos.append(m)

    if restante > 0:
        raise EstoqueError(
            f"Estoque insuficiente para o produto '{produto.nome}'. "
            f"Faltam {restante} {produto.unidade_medida}."
        )

    if lote is not None:
        m = Movimento.objects.create(
            produto=produto, lote=lote, tipo="SAIDA", motivo=motivo,
            quantidade=quantidade, responsavel=responsavel,
            data_movimento=timezone.now(),
            observacoes=observacoes,
            created_by=usuario, updated_by=usuario,
        )
        movimentos.append(m)

    return movimentos[0] if len(movimentos) == 1 else movimentos


# ============================================================================
# 4) Ajuste de inventário
# ============================================================================
@transaction.atomic
def registrar_ajuste(
    *,
    produto: Produto,
    quantidade: Decimal,
    direcao: str,  # "ENTRADA" ou "SAIDA"
    motivo_detalhado: str = "",
    observacoes: str = "",
    lote: Optional[Lote] = None,
    usuario=None,
) -> Movimento:
    """
    Registra um ajuste manual de inventário.

    - direcao="ENTRADA" aumenta o estoque (ex: contagem maior que o sistema).
    - direcao="SAIDA"   diminui o estoque (ex: perda não registrada, contagem menor).
    """
    if quantidade <= 0:
        raise EstoqueError("A quantidade do ajuste deve ser maior que zero.")
    if direcao not in ("ENTRADA", "SAIDA"):
        raise EstoqueError("Direção do ajuste inválida.")

    motivo = "AJUSTE_ENTRADA" if direcao == "ENTRADA" else "AJUSTE_SAIDA"
    obs_final = f"[AJUSTE] {motivo_detalhado}".strip()
    if observacoes:
        obs_final = f"{obs_final} — {observacoes}"

    if direcao == "ENTRADA":
        # Cria movimento de entrada diretamente, sem criar lote novo
        # (o ajuste vai para o estoque "geral" sem lote específico).
        return Movimento.objects.create(
            produto=produto,
            lote=None,
            tipo="ENTRADA",
            motivo=motivo,
            quantidade=quantidade,
            valor_unitario=valor_medio_unitario(produto) or None,
            data_movimento=timezone.now(),
            observacoes=obs_final,
            created_by=usuario,
            updated_by=usuario,
        )
    else:
        return registrar_saida(
            produto=produto,
            quantidade=quantidade,
            motivo=motivo,
            observacoes=obs_final,
            lote=lote,
            usuario=usuario,
        )


# ============================================================================
# 5) Cancelamento de movimento
# ============================================================================
@transaction.atomic
def cancelar_movimento(movimento: Movimento, motivo_cancelamento: str, usuario=None) -> Movimento:
    """
    Cancela um movimento repondo o estoque (se entrada) ou consumindo
    (se saída). O movimento original NÃO é apagado — recebe
    `cancelado=True` e `motivo_cancelamento`.

    Movimentos de ajuste também podem ser cancelados.
    """
    if movimento.cancelado:
        raise EstoqueError("Este movimento já foi cancelado.")

    obs = f"[CANCELAMENTO] {motivo_cancelamento}".strip()

    if movimento.tipo == "ENTRADA":
        # Reverte: retira do lote (se houver) ou do estoque total
        if movimento.lote:
            movimento.lote.quantidade_atual = max(
                Decimal("0"),
                movimento.lote.quantidade_atual - movimento.quantidade
            )
            movimento.lote.updated_by = usuario
            movimento.lote.save(update_fields=["quantidade_atual", "updated_at", "updated_by"])
        # Não há "saída fantasma" - apenas o cancelamento do registro.
    else:  # SAIDA
        # Reverte: devolve ao lote (se houver) ou ao estoque
        if movimento.lote:
            movimento.lote.quantidade_atual += movimento.quantidade
            movimento.lote.updated_by = usuario
            movimento.lote.save(update_fields=["quantidade_atual", "updated_at", "updated_by"])
        else:
            # Recria o lote "perdido"? Não temos como saber qual era.
            # Se a saída usou FEFO, na prática o cancelamento ficaria
            # registrado mas o estoque total ficaria inconsistente.
            # Para evitar isso, obrigamos cancelamento apenas de
            # movimentos com lote conhecido.
            raise EstoqueError(
                "Não é possível cancelar uma saída sem lote definido "
                "(consumiu vários lotes via FEFO). Use um ajuste de inventário."
            )

    movimento.cancelado = True
    movimento.motivo_cancelamento = obs
    movimento.updated_by = usuario
    movimento.save(update_fields=["cancelado", "motivo_cancelamento", "updated_at", "updated_by"])
    return movimento
