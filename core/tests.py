"""
Testes do módulo core (Fase 4 — listagem de produtos com estoque anotado).

Garante que:
- A annotation qtd_estoque está correta (soma ENTRADA - soma SAIDA, ignorando cancelados)
- A listagem faz no máximo 2 queries (sem N+1)
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from core.models import Categoria, Produto
from stock.services import registrar_entrada, registrar_saida


User = get_user_model()


def _criar_produto(nome="P", estoque_minimo=Decimal("5"), estoque_ideal=Decimal("20"),
                   **kwargs):
    cat = Categoria.objects.create(nome="Cat-" + nome, cor="#000000")
    defaults = dict(
        nome=nome, codigo_interno="COD-" + nome, categoria=cat,
        unidade_medida="KG",
    )
    defaults.update(kwargs)
    p = Produto.objects.create(estoque_minimo=estoque_minimo,
                               estoque_ideal=estoque_ideal,
                               **defaults)
    return p


def _dias(n):
    return date.today() + timedelta(days=n)


class ProdutoListEstoqueAnotadoTests(TestCase):
    """A listagem de produtos calcula o estoque atual via annotation (sem N+1)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="op", password="pw", is_active=True, is_staff=True,
        )
        self.client.force_login(self.user)
        self.url = reverse("core:produto_list")

    def test_annotation_reflete_movimentos(self):
        p = _criar_produto(nome="A")
        registrar_entrada(
            produto=p, quantidade=Decimal("10"), data_entrada=_dias(0),
            data_validade=_dias(10), numero_lote="L1", valor_unitario=Decimal("2"),
        )
        registrar_entrada(
            produto=p, quantidade=Decimal("3"), data_entrada=_dias(0),
            data_validade=_dias(10), numero_lote="L2", valor_unitario=Decimal("2"),
        )
        lote = p.lotes.first()
        registrar_saida(produto=p, quantidade=Decimal("4"), motivo="CONSUMO_INTERNO",
                        lote=lote)

        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        for prod in resp.context["produtos"]:
            if prod.pk == p.pk:
                produto = prod
                break
        # 10 + 3 - 4 = 9
        self.assertEqual(produto.qtd_estoque, Decimal("9"))

    def test_annotation_ignora_movimentos_cancelados(self):
        p = _criar_produto(nome="B")
        m = registrar_entrada(
            produto=p, quantidade=Decimal("10"), data_entrada=_dias(0),
            data_validade=_dias(10), numero_lote="L1", valor_unitario=Decimal("2"),
        )
        from stock.services import cancelar_movimento
        cancelar_movimento(m, motivo_cancelamento="erro")

        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        for prod in resp.context["produtos"]:
            if prod.pk == p.pk:
                produto = prod
                break
        self.assertEqual(produto.qtd_estoque, Decimal("0"))

    def test_listagem_nao_faz_n1_para_estoque(self):
        # Cria 5 produtos, cada um com 1 entrada → estoque 10
        for i in range(5):
            p = _criar_produto(nome=f"P{i}")
            registrar_entrada(
                produto=p, quantidade=Decimal("10"), data_entrada=_dias(0),
                data_validade=_dias(10), numero_lote=f"L{i}",
                valor_unitario=Decimal("1"),
            )

        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get(self.url)
            # Acessa a annotation em cada produto (simula o template)
            for prod in resp.context["produtos"]:
                _ = prod.qtd_estoque

        # Garante que NÃO há N+1: o estoque é resolvido em uma única
        # query ao core_produto (com JOIN em stock_movimento) — não deve
        # haver queries adicionais em stock_movimento para cada produto.
        queries_produto = [q for q in ctx.captured_queries
                           if "core_produto" in q["sql"].lower()
                           and "select" in q["sql"].lower()[:20]]
        queries_movimento = [q for q in ctx.captured_queries
                             if "stock_movimento" in q["sql"].lower()]

        # Esperado: 2 queries em core_produto (1 do COUNT para paginação
        # + 1 do SELECT com JOIN em movimento).
        # Se vir 3+, há N+1 (uma query extra por produto).
        self.assertLessEqual(
            len(queries_produto), 2,
            f"N+1 em core_produto: {len(queries_produto)} queries (esperado ≤ 2)",
        )
        # Mesma lógica para movimento: 2 queries no máximo (COUNT + SELECT).
        self.assertLessEqual(
            len(queries_movimento), 2,
            f"N+1 em stock_movimento: {len(queries_movimento)} queries (esperado ≤ 2)",
        )

    def test_listagem_renderiza_valor_estoque(self):
        p = _criar_produto(nome="Render")
        registrar_entrada(
            produto=p, quantidade=Decimal("7"), data_entrada=_dias(0),
            data_validade=_dias(10), numero_lote="L1", valor_unitario=Decimal("1"),
        )
        resp = self.client.get(self.url)
        self.assertContains(resp, ">7<")
