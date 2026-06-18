"""
Testes do módulo de inteligência (Fase 3).

Cobre:
- quantidade_recomendada_compra (fórmula baseada em estoque_ideal)
- View intelligence_home (200, seções, contexto)
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Categoria, Produto
from stock.services import registrar_entrada

from .analises import quantidade_recomendada_compra
from . import views as intelligence_views


User = get_user_model()


def _criar_produto(nome="Teste", **kwargs):
    cat = Categoria.objects.create(nome="Cat-" + nome, cor="#000000")
    defaults = dict(
        nome=nome,
        codigo_interno="COD-" + nome,
        categoria=cat,
        unidade_medida="UN",
        estoque_minimo=Decimal("5"),
        estoque_ideal=Decimal("20"),
    )
    defaults.update(kwargs)
    return Produto.objects.create(**defaults)


def _dias(n):
    return date.today() + timedelta(days=n)


class QuantidadeRecomendadaCompraTests(TestCase):
    """quantidade_recomendada_compra usa estoque_ideal como alvo."""

    def test_retorna_zero_se_estoque_ideal_zero_ou_nao_definido(self):
        p = _criar_produto(nome="SemIdeal", estoque_ideal=Decimal("0"))
        # Cria entrada para ter estoque > 0
        registrar_entrada(
            produto=p, quantidade=Decimal("10"), data_entrada=_dias(0),
            data_validade=_dias(10), numero_lote="L1",
            valor_unitario=Decimal("1"),
        )
        self.assertEqual(quantidade_recomendada_compra(p), Decimal("0"))

    def test_retorna_zero_se_estoque_ja_atinge_ideal(self):
        p = _criar_produto(nome="Ok", estoque_ideal=Decimal("20"))
        registrar_entrada(
            produto=p, quantidade=Decimal("20"), data_entrada=_dias(0),
            data_validade=_dias(10), numero_lote="L1",
            valor_unitario=Decimal("1"),
        )
        self.assertEqual(quantidade_recomendada_compra(p), Decimal("0"))

    def test_retorna_zero_se_estoque_ultrapassa_ideal(self):
        p = _criar_produto(nome="Sobre", estoque_ideal=Decimal("20"))
        registrar_entrada(
            produto=p, quantidade=Decimal("50"), data_entrada=_dias(0),
            data_validade=_dias(10), numero_lote="L1",
            valor_unitario=Decimal("1"),
        )
        self.assertEqual(quantidade_recomendada_compra(p), Decimal("0"))

    def test_calcula_falta_para_atingir_estoque_ideal(self):
        p = _criar_produto(nome="Falta", estoque_ideal=Decimal("30"))
        registrar_entrada(
            produto=p, quantidade=Decimal("7"), data_entrada=_dias(0),
            data_validade=_dias(10), numero_lote="L1",
            valor_unitario=Decimal("1"),
        )
        # estoque_atual=7, ideal=30 → falta 23
        self.assertEqual(quantidade_recomendada_compra(p), Decimal("23"))

    def test_calcula_falta_para_produto_sem_movimentos(self):
        p = _criar_produto(nome="Vazio", estoque_ideal=Decimal("30"))
        # estoque_atual=0, ideal=30 → falta 30
        self.assertEqual(quantidade_recomendada_compra(p), Decimal("30"))


class IntelligenceHomeViewTests(TestCase):
    """View /inteligencia/ deve renderizar 200 com seções para usuário autenticado."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="op", password="pw12345", is_active=True,
        )
        self.url = reverse("intelligence:home")

    def test_redireciona_anonimo_para_login(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("contas/login", resp.url)

    def test_retorna_200_autenticado(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_renderiza_as_secoes_principais(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        for section in (
            "Ruptura iminente",
            "Sugestões de compra",
            "Anomalias de consumo",
            "Estoque abaixo do mínimo",
            "Excesso de estoque",
        ):
            self.assertContains(resp, section, msg_prefix=f"section missing: {section}")

    def test_renderiza_kpis_zero_quando_sem_produtos(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.context["rupturas_count"], 0)
        self.assertEqual(resp.context["estoque_baixo_count"], 0)
        self.assertEqual(resp.context["sugestoes_count"], 0)
        self.assertEqual(resp.context["excessos_count"], 0)
        self.assertEqual(resp.context["anomalias_count"], 0)

    def test_detecta_produto_em_sugestoes_quando_abaixo_do_ideal(self):
        p = _criar_produto(nome="ParaComprar", estoque_ideal=Decimal("30"))
        registrar_entrada(
            produto=p, quantidade=Decimal("3"), data_entrada=_dias(0),
            data_validade=_dias(10), numero_lote="L1",
            valor_unitario=Decimal("2"),
        )
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.context["sugestoes_count"], 1)
        sugestao = resp.context["sugestoes"][0]
        produto, qtd, valor = sugestao
        self.assertEqual(produto.pk, p.pk)
        self.assertEqual(qtd, Decimal("27"))  # 30 - 3
        self.assertEqual(valor, Decimal("54.00"))  # 27 * 2

    def test_detecta_produto_em_excesso(self):
        p = _criar_produto(nome="Excesso", estoque_ideal=Decimal("10"))
        registrar_entrada(
            produto=p, quantidade=Decimal("20"), data_entrada=_dias(0),
            data_validade=_dias(10), numero_lote="L1",
            valor_unitario=Decimal("1"),
        )
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.context["excessos_count"], 1)
        prod, excedente = resp.context["excessos"][0]
        self.assertEqual(prod.pk, p.pk)
        self.assertEqual(excedente, Decimal("10.000"))

    def test_detecta_produto_com_estoque_baixo(self):
        p = _criar_produto(nome="Baixo", estoque_minimo=Decimal("5"))
        # Estoque_atual = 0
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.context["estoque_baixo_count"], 1)

    def test_ignora_produtos_inativos(self):
        p = _criar_produto(nome="Inativo", estoque_ideal=Decimal("10"))
        p.ativo = False
        p.save()
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.context["sugestoes_count"], 0)
        self.assertEqual(resp.context["estoque_baixo_count"], 0)


class IntelligenceViewHelpersTests(TestCase):
    """Cobre funções auxiliares do módulo views."""

    def test_calcular_sugestoes_ordenado_por_urgencia(self):
        # produtos com diferentes graus de cobertura
        p1 = _criar_produto(nome="P1", estoque_ideal=Decimal("100"))  # sem entrada
        p2 = _criar_produto(nome="P2", estoque_ideal=Decimal("100"))  # com entrada 95
        p3 = _criar_produto(nome="P3", estoque_ideal=Decimal("100"))  # com entrada 50
        registrar_entrada(produto=p2, quantidade=Decimal("95"), data_entrada=_dias(0),
                          data_validade=_dias(10), numero_lote="L2",
                          valor_unitario=Decimal("1"))
        registrar_entrada(produto=p3, quantidade=Decimal("50"), data_entrada=_dias(0),
                          data_validade=_dias(10), numero_lote="L3",
                          valor_unitario=Decimal("1"))
        sugestoes = intelligence_views._calcular_sugestoes([p1, p2, p3])
        # p1 (0/100) é mais urgente que p3 (50/100), que é mais urgente que p2 (95/100)
        self.assertEqual(sugestoes[0][0].nome, "P1")
        self.assertEqual(sugestoes[1][0].nome, "P3")
        self.assertEqual(sugestoes[2][0].nome, "P2")
