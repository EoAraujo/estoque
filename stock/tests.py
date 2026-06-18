"""
Testes do módulo de estoque (Fase 2).

Cobre as regras de negócio do service layer:
- Entrada (criação de lote + movimento)
- Saída (FEFO + rateio + bloqueio de estoque insuficiente)
- Ajuste de inventário
- Cancelamento de movimento (imutável)
- Cálculo de valor médio ponderado
- Cálculo de quantidade atual a partir do histórico
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.models import Categoria, Fornecedor, Produto
from stock.models import Lote, Movimento
from stock.services import (
    EstoqueError,
    cancelar_movimento,
    registrar_ajuste,
    registrar_entrada,
    registrar_saida,
    valor_medio_unitario,
    valor_total_estoque_produto,
)
from intelligence.analises import quantidade_recomendada_compra


User = get_user_model()


def _criar_produto(nome="Tomate", controla_validade=True, **kwargs):
    cat = Categoria.objects.create(nome="Cat-" + nome, cor="#000000")
    defaults = dict(
        nome=nome,
        codigo_interno="COD-" + nome,
        categoria=cat,
        unidade_medida="KG",
        controla_validade=controla_validade,
        estoque_minimo=Decimal("5"),
        estoque_ideal=Decimal("30"),
    )
    defaults.update(kwargs)
    return Produto.objects.create(**defaults)


def _dias(n):
    return date.today() + timedelta(days=n)


class RegistrarEntradaTests(TestCase):
    """Testes do serviço registrar_entrada."""

    def setUp(self):
        self.produto = _criar_produto()

    def test_cria_lote_e_movimento_quando_controla_validade(self):
        m = registrar_entrada(
            produto=self.produto,
            quantidade=Decimal("10"),
            data_entrada=_dias(0),
            data_validade=_dias(15),
            numero_lote="L-001",
            valor_unitario=Decimal("5.00"),
        )
        self.assertEqual(m.tipo, "ENTRADA")
        self.assertEqual(m.quantidade, Decimal("10"))
        self.assertEqual(m.valor_total, Decimal("50.00"))
        self.assertIsNotNone(m.lote)
        self.assertEqual(m.lote.quantidade_atual, Decimal("10"))
        self.assertEqual(m.lote.numero_lote, "L-001")

    def test_nao_cria_lote_quando_nao_controla_validade(self):
        p = _criar_produto(nome="Acucar", controla_validade=False)
        m = registrar_entrada(
            produto=p,
            quantidade=Decimal("20"),
            data_entrada=_dias(0),
        )
        self.assertIsNone(m.lote)
        self.assertEqual(m.quantidade, Decimal("20"))

    def test_exige_data_validade_quando_controla_validade(self):
        with self.assertRaises(EstoqueError) as ctx:
            registrar_entrada(
                produto=self.produto,
                quantidade=Decimal("10"),
                data_entrada=_dias(0),
                data_validade=None,
            )
        self.assertIn("validade", str(ctx.exception).lower())

    def test_quantidade_zero_ou_negativa_rejeitada(self):
        for q in (Decimal("0"), Decimal("-1")):
            with self.subTest(q=q):
                with self.assertRaises(EstoqueError):
                    registrar_entrada(
                        produto=self.produto,
                        quantidade=q,
                        data_entrada=_dias(0),
                        data_validade=_dias(10),
                    )


class RegistrarSaidaTestsFEFO(TestCase):
    """Testes do FEFO (consumo do lote que vence primeiro)."""

    def setUp(self):
        self.produto = _criar_produto()
        # Lote 1: vence em 30 dias (mais distante)
        self.l1 = registrar_entrada(
            produto=self.produto, quantidade=Decimal("10"),
            data_entrada=_dias(0), data_validade=_dias(30),
            numero_lote="L-30", valor_unitario=Decimal("5"),
        ).lote
        # Lote 2: vence em 10 dias (mais próximo, deve sair primeiro)
        self.l2 = registrar_entrada(
            produto=self.produto, quantidade=Decimal("10"),
            data_entrada=_dias(0), data_validade=_dias(10),
            numero_lote="L-10", valor_unitario=Decimal("5"),
        ).lote
        # Lote 3: vence em 5 dias (ainda mais próximo)
        self.l3 = registrar_entrada(
            produto=self.produto, quantidade=Decimal("10"),
            data_entrada=_dias(0), data_validade=_dias(5),
            numero_lote="L-05", valor_unitario=Decimal("5"),
        ).lote

    def test_fefo_consome_lote_que_vence_primeiro(self):
        # Saída de 5: deve consumir do l3 (vence em 5 dias)
        registrar_saida(
            produto=self.produto, quantidade=Decimal("5"),
            motivo="PRODUCAO",
        )
        self.l3.refresh_from_db()
        self.l2.refresh_from_db()
        self.l1.refresh_from_db()
        self.assertEqual(self.l3.quantidade_atual, Decimal("5"))
        self.assertEqual(self.l2.quantidade_atual, Decimal("10"))
        self.assertEqual(self.l1.quantidade_atual, Decimal("10"))

    def test_fefo_rateia_entre_multiplos_lotes(self):
        # Saída de 12: deve consumir 10 do l3 + 2 do l2
        resultado = registrar_saida(
            produto=self.produto, quantidade=Decimal("12"),
            motivo="PRODUCAO",
        )
        self.assertIsInstance(resultado, list)
        self.assertEqual(len(resultado), 2)
        self.l3.refresh_from_db()
        self.l2.refresh_from_db()
        self.l1.refresh_from_db()
        self.assertEqual(self.l3.quantidade_atual, Decimal("0"))
        self.assertEqual(self.l2.quantidade_atual, Decimal("8"))
        self.assertEqual(self.l1.quantidade_atual, Decimal("10"))

    def test_saida_direcionada_a_lote_especifico(self):
        # Saída de 8 do l2 (não do l3, que vence antes)
        m = registrar_saida(
            produto=self.produto, quantidade=Decimal("8"),
            motivo="PRODUCAO", lote=self.l2,
        )
        self.assertEqual(m.lote, self.l2)
        self.l2.refresh_from_db()
        self.l3.refresh_from_db()
        self.assertEqual(self.l2.quantidade_atual, Decimal("2"))
        self.assertEqual(self.l3.quantidade_atual, Decimal("10"))  # intacto

    def test_saida_sem_lote_retorna_movimento_unico_se_cabe_em_um(self):
        # Saída de 3: cabe em 1 lote (l3)
        resultado = registrar_saida(
            produto=self.produto, quantidade=Decimal("3"),
            motivo="PRODUCAO",
        )
        self.assertNotIsInstance(resultado, list)
        self.assertEqual(resultado.lote, self.l3)


class RegistrarSaidaValidacoesTestCase(TestCase):
    """Testes de validação de estoque e quantidade."""

    def setUp(self):
        self.produto = _criar_produto()
        registrar_entrada(
            produto=self.produto, quantidade=Decimal("5"),
            data_entrada=_dias(0), data_validade=_dias(10),
        )

    def test_bloqueia_saida_maior_que_estoque(self):
        with self.assertRaises(EstoqueError) as ctx:
            registrar_saida(produto=self.produto, quantidade=Decimal("999"), motivo="PRODUCAO")
        self.assertIn("insuficiente", str(ctx.exception).lower())

    def test_bloqueia_saida_de_lote_sem_saldo(self):
        # Cria outro lote vazio
        lote_vazio = Lote.objects.create(
            produto=self.produto, numero_lote="VAZIO",
            data_entrada=_dias(0), data_validade=_dias(20),
            quantidade_inicial=Decimal("0"), quantidade_atual=Decimal("0"),
        )
        with self.assertRaises(EstoqueError):
            registrar_saida(produto=self.produto, quantidade=Decimal("1"), motivo="PRODUCAO", lote=lote_vazio)

    def test_quantidade_zero_ou_negativa_rejeitada(self):
        for q in (Decimal("0"), Decimal("-5")):
            with self.subTest(q=q):
                with self.assertRaises(EstoqueError):
                    registrar_saida(produto=self.produto, quantidade=q, motivo="PRODUCAO")


class RegistrarAjusteTests(TestCase):
    """Testes do ajuste de inventário."""

    def setUp(self):
        self.produto = _criar_produto()
        registrar_entrada(
            produto=self.produto, quantidade=Decimal("20"),
            data_entrada=_dias(0), data_validade=_dias(30),
        )

    def test_ajuste_entrada_aumenta_estoque(self):
        registrar_ajuste(
            produto=self.produto, quantidade=Decimal("3"),
            direcao="ENTRADA", motivo_detalhado="Inventário",
        )
        # 20 da entrada + 3 do ajuste = 23
        self.assertEqual(self.produto.quantidade_atual, Decimal("23"))

    def test_ajuste_entrada_nao_cria_lote_novo(self):
        m = registrar_ajuste(
            produto=self.produto, quantidade=Decimal("2"),
            direcao="ENTRADA", motivo_detalhado="Sobra contagem",
        )
        self.assertEqual(m.tipo, "ENTRADA")
        self.assertIsNone(m.lote)

    def test_ajuste_saida_diminui_estoque(self):
        registrar_ajuste(
            produto=self.produto, quantidade=Decimal("5"),
            direcao="SAIDA", motivo_detalhado="Perda",
        )
        self.assertEqual(self.produto.quantidade_atual, Decimal("15"))

    def test_ajuste_saida_sem_lote_falha_se_nao_tem_lotes_com_saldo(self):
        with self.assertRaises(EstoqueError):
            registrar_ajuste(
                produto=self.produto, quantidade=Decimal("999"),
                direcao="SAIDA", motivo_detalhado="Inventário",
            )

    def test_direcao_invalida_rejeitada(self):
        with self.assertRaises(EstoqueError):
            registrar_ajuste(
                produto=self.produto, quantidade=Decimal("1"),
                direcao="LATERAL", motivo_detalhado="x",
            )


class CancelarMovimentoTests(TestCase):
    """Testes de cancelamento (movimentos são imutáveis, estoque reverte)."""

    def setUp(self):
        self.produto = _criar_produto()
        self.mov = registrar_entrada(
            produto=self.produto, quantidade=Decimal("10"),
            data_entrada=_dias(0), data_validade=_dias(15),
            numero_lote="LX",
        )
        self.lote = self.mov.lote
        # Faz uma saída para consumir parte do lote
        self.saida = registrar_saida(
            produto=self.produto, quantidade=Decimal("3"),
            motivo="PRODUCAO",
        )

    def test_cancelar_entrada_reduz_lote(self):
        saldo_antes = self.lote.quantidade_atual
        cancelar_movimento(self.mov, motivo_cancelamento="NF cancelada")
        self.lote.refresh_from_db()
        self.mov.refresh_from_db()
        self.assertTrue(self.mov.cancelado)
        self.assertEqual(
            self.lote.quantidade_atual,
            saldo_antes - self.mov.quantidade,
        )

    def test_cancelar_saida_devolve_ao_lote(self):
        # A saída consumiu 3 do lote que tinha 10 → lote com 7
        # Mas como houve FEFO e existem 2 lotes (entrada original e
        # ajuste), verificamos a soma do estoque
        estoque_antes = self.produto.quantidade_atual
        cancelar_movimento(self.saida, motivo_cancelamento="Erro de lançamento")
        self.produto.refresh_from_db()
        self.assertEqual(
            self.produto.quantidade_atual,
            estoque_antes + self.saida.quantidade,
        )

    def test_cancelar_movimento_ja_cancelado_falha(self):
        cancelar_movimento(self.mov, motivo_cancelamento="x")
        with self.assertRaises(EstoqueError):
            cancelar_movimento(self.mov, motivo_cancelamento="y")

    def test_cancelar_saida_sem_lote_falha(self):
        # Cria um movimento de ajuste de entrada (sem lote) e tenta "cancelar como saída"
        m_ajuste = registrar_ajuste(
            produto=self.produto, quantidade=Decimal("1"),
            direcao="ENTRADA", motivo_detalhado="x",
        )
        # Agora converte manualmente em uma "saída" sem lote
        m_ajuste.tipo = "SAIDA"
        m_ajuste.lote = None
        m_ajuste.save()
        with self.assertRaises(EstoqueError) as ctx:
            cancelar_movimento(m_ajuste, motivo_cancelamento="tentativa")
        self.assertIn("sem lote", str(ctx.exception).lower())


class ValorMedioTests(TestCase):
    """Testes do cálculo de valor médio ponderado."""

    def setUp(self):
        self.produto = _criar_produto()

    def test_sem_movimentos_retorna_zero(self):
        self.assertEqual(valor_medio_unitario(self.produto), Decimal("0"))

    def test_media_ponderada_pondera_por_quantidade(self):
        # 10 kg a R$ 4,00 + 10 kg a R$ 6,00 = média 5,00
        registrar_entrada(
            produto=self.produto, quantidade=Decimal("10"),
            data_entrada=_dias(0), data_validade=_dias(30),
            valor_unitario=Decimal("4.00"),
        )
        registrar_entrada(
            produto=self.produto, quantidade=Decimal("10"),
            data_entrada=_dias(0), data_validade=_dias(60),
            valor_unitario=Decimal("6.00"),
        )
        self.assertEqual(valor_medio_unitario(self.produto), Decimal("5.0000"))

    def test_entradas_antigas_nao_pesam(self):
        # Entrada recente a R$ 5
        registrar_entrada(
            produto=self.produto, quantidade=Decimal("10"),
            data_entrada=_dias(0), data_validade=_dias(30),
            valor_unitario=Decimal("5.00"),
        )
        # Entrada de 100 dias atrás a R$ 1 (fora da janela de 90 dias)
        m = registrar_entrada(
            produto=self.produto, quantidade=Decimal("100"),
            data_entrada=_dias(0), data_validade=_dias(60),
            valor_unitario=Decimal("1.00"),
        )
        # Ajusta a data do movimento para 100 dias atrás
        m.data_movimento = timezone.now() - timedelta(days=100)
        m.save()
        # A média deve ser apenas R$ 5,00
        self.assertEqual(valor_medio_unitario(self.produto), Decimal("5.0000"))

    def test_valor_total_multiplica_qtd_por_media(self):
        registrar_entrada(
            produto=self.produto, quantidade=Decimal("20"),
            data_entrada=_dias(0), data_validade=_dias(30),
            valor_unitario=Decimal("3.50"),
        )
        total = valor_total_estoque_produto(self.produto)
        self.assertEqual(total, Decimal("70.00"))


class QuantidadeAtualTests(TestCase):
    """Testes do cálculo de estoque via histórico de movimentações."""

    def setUp(self):
        self.produto = _criar_produto()

    def test_inicial_zero(self):
        self.assertEqual(self.produto.quantidade_atual, Decimal("0"))

    def test_soma_entradas_menos_saidas(self):
        registrar_entrada(
            produto=self.produto, quantidade=Decimal("30"),
            data_entrada=_dias(0), data_validade=_dias(30),
        )
        registrar_saida(produto=self.produto, quantidade=Decimal("8"), motivo="PRODUCAO")
        registrar_saida(produto=self.produto, quantidade=Decimal("5"), motivo="PRODUCAO")
        # 30 - 8 - 5 = 17
        self.assertEqual(self.produto.quantidade_atual, Decimal("17"))

    def test_movimentos_cancelados_nao_pesam(self):
        m = registrar_entrada(
            produto=self.produto, quantidade=Decimal("10"),
            data_entrada=_dias(0), data_validade=_dias(30),
        )
        # 10 em estoque
        self.assertEqual(self.produto.quantidade_atual, Decimal("10"))
        # Cancela → 0
        cancelar_movimento(m, motivo_cancelamento="teste")
        self.assertEqual(self.produto.quantidade_atual, Decimal("0"))

    def test_ajuste_entrada_conta_no_total(self):
        # Sem criar lote
        registrar_ajuste(
            produto=self.produto, quantidade=Decimal("3"),
            direcao="ENTRADA", motivo_detalhado="x",
        )
        self.assertEqual(self.produto.quantidade_atual, Decimal("3"))


class RecomendacaoCompraTests(TestCase):
    """Testes da sugestão de compra."""

    def test_sugere_quantidade_para_atingir_ideal(self):
        p = _criar_produto(
            estoque_minimo=Decimal("5"),
            estoque_ideal=Decimal("30"),
        )
        registrar_entrada(
            produto=p, quantidade=Decimal("8"),
            data_entrada=_dias(0), data_validade=_dias(30),
        )
        # 30 - 8 = 22
        self.assertEqual(
            quantidade_recomendada_compra(p), Decimal("22"),
        )

    def test_nao_recomenda_se_estoque_acima_do_ideal(self):
        p = _criar_produto(
            estoque_minimo=Decimal("5"),
            estoque_ideal=Decimal("30"),
        )
        registrar_entrada(
            produto=p, quantidade=Decimal("50"),
            data_entrada=_dias(0), data_validade=_dias(30),
        )
        self.assertEqual(
            quantidade_recomendada_compra(p), Decimal("0"),
        )

    def test_zero_se_produto_sem_estoque_ideal_definido(self):
        p = _criar_produto(estoque_ideal=Decimal("0"))
        self.assertEqual(
            quantidade_recomendada_compra(p), Decimal("0"),
        )
