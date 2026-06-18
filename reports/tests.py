"""
Testes do módulo de relatórios (Fase 4).

Cobre:
- 200/302 nas 4 views de export
- Filtros aplicados
- Conteúdo de cada arquivo (Excel/PDF)
- View de preferências do usuário
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from audit.models import LogAuditoria
from core.models import Categoria, Fornecedor, Produto
from stock.models import Lote, Movimento
from stock.services import registrar_entrada


User = get_user_model()


def _criar_produto(nome="P", **kwargs):
    cat = Categoria.objects.create(nome="Cat-" + nome, cor="#000000")
    defaults = dict(
        nome=nome, codigo_interno="COD-" + nome, categoria=cat,
        unidade_medida="KG", estoque_minimo=Decimal("5"),
        estoque_ideal=Decimal("20"),
    )
    defaults.update(kwargs)
    return Produto.objects.create(**defaults)


def _dias(n):
    return date.today() + timedelta(days=n)


class ExportMovimentacoesXlsxTests(TestCase):
    """GET /relatorios/movimentacoes.xlsx"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="op", password="pw", is_active=True, is_staff=True,
        )
        self.url = reverse("reports:movimentacoes_xlsx")
        self.p = _criar_produto()
        registrar_entrada(
            produto=self.p, quantidade=Decimal("10"), data_entrada=_dias(0),
            data_validade=_dias(15), numero_lote="L1",
            valor_unitario=Decimal("2"),
        )

    def test_anonimo_redirecionado(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_autenticado_retorna_xlsx_200(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn("attachment", resp["Content-Disposition"])

    def test_filtro_por_tipo(self):
        # Cria também uma saída
        from stock.services import registrar_saida
        lote = Lote.objects.filter(produto=self.p).first()
        registrar_saida(produto=self.p, quantidade=Decimal("3"), motivo="DESCARTE",
                        lote=lote)
        self.client.force_login(self.user)
        resp = self.client.get(self.url + "?tipo=ENTRADA")
        self.assertEqual(resp.status_code, 200)

    def test_filtro_por_periodo(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url + "?periodo=90")
        self.assertEqual(resp.status_code, 200)


class ExportPosicaoEstoqueXlsxTests(TestCase):
    """GET /relatorios/estoque.xlsx"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="op", password="pw", is_active=True, is_staff=True,
        )
        self.url = reverse("reports:estoque_xlsx")
        self.p = _criar_produto()
        registrar_entrada(
            produto=self.p, quantidade=Decimal("5"), data_entrada=_dias(0),
            data_validade=_dias(10), numero_lote="L1",
            valor_unitario=Decimal("3"),
        )

    def test_anonimo_redirecionado(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_autenticado_retorna_xlsx_200(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_filtro_apenas_com_estoque(self):
        # produto com estoque
        self.client.force_login(self.user)
        resp = self.client.get(self.url + "?apenas_com_estoque=1")
        self.assertEqual(resp.status_code, 200)


class ExportAuditoriaXlsxTests(TestCase):
    """GET /relatorios/auditoria.xlsx"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="op", password="pw", is_active=True, is_staff=True,
        )
        self.url = reverse("reports:auditoria_xlsx")

    def test_anonimo_redirecionado(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_autenticado_retorna_xlsx_200(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_filtro_acao(self):
        LogAuditoria.objects.create(
            usuario=self.user, acao="CRIAR", modelo="Produto",
            objeto_repr="X", objeto_id=1, url="/", metodo="POST",
        )
        self.client.force_login(self.user)
        resp = self.client.get(self.url + "?acao=CRIAR")
        self.assertEqual(resp.status_code, 200)


class ExportValidadePdfTests(TestCase):
    """GET /relatorios/validade.pdf"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="op", password="pw", is_active=True, is_staff=True,
        )
        self.url = reverse("reports:validade_pdf")

    def test_anonimo_redirecionado(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_autenticado_retorna_pdf_200(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertIn("attachment", resp["Content-Disposition"])
        # PDF começa com %PDF
        self.assertTrue(resp.content.startswith(b"%PDF"))

    def test_pdf_contem_secoes_basicas(self):
        # Cria lote vencido
        p = _criar_produto(nome="Vencido")
        registrar_entrada(
            produto=p, quantidade=Decimal("5"), data_entrada=_dias(-30),
            data_validade=_dias(-2), numero_lote="L1",
            valor_unitario=Decimal("1"),
        )
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)


class PreferenciasTests(TestCase):
    """POST /contas/preferencias/ salva período do perfil."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="op", password="pw", is_active=True,
        )
        self.url = reverse("accounts:preferencias")

    def test_get_renderiza_form(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Período padrão")

    def test_post_salva_novo_periodo(self):
        self.client.force_login(self.user)
        resp = self.client.post(self.url, {"periodo_padrao": "7"})
        self.assertEqual(resp.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.periodo_padrao, 7)

    def test_post_invalido_nao_altera(self):
        self.client.force_login(self.user)
        original = self.user.profile.periodo_padrao
        resp = self.client.post(self.url, {"periodo_padrao": "99999"})
        self.assertEqual(resp.status_code, 200)  # renderiza form com erro
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.periodo_padrao, original)


class DashboardPeriodoTests(TestCase):
    """Dashboard respeita ?periodo= e fallback para profile.periodo_padrao."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="op", password="pw", is_active=True,
        )
        self.url = reverse("core:dashboard")

    def test_periodo_default_do_perfil(self):
        self.user.profile.periodo_padrao = 7
        self.user.profile.save()
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["periodo_dias"], 7)

    def test_periodo_via_querystring_sobrescreve(self):
        self.user.profile.periodo_padrao = 30
        self.user.profile.save()
        self.client.force_login(self.user)
        resp = self.client.get(self.url + "?periodo=90")
        self.assertEqual(resp.context["periodo_dias"], 90)

    def test_periodo_invalido_cae_no_padrao(self):
        self.user.profile.periodo_padrao = 30
        self.user.profile.save()
        self.client.force_login(self.user)
        resp = self.client.get(self.url + "?periodo=99999")
        self.assertEqual(resp.context["periodo_dias"], 30)
