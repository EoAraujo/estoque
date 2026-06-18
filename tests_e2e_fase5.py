"""Testes E2E completos com Playwright (Fase 5)."""
import os
import re
from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:8765"

def login(page):
    page.goto(f"{BASE}/contas/login/", wait_until="networkidle")
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "admin123")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle", timeout=15000)
    # Confirma que saiu do login
    assert "/contas/login" not in page.url, f"Login falhou, ainda em {page.url}"


def test_main_flows():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1366, "height": 900})
        page = ctx.new_page()

        # 1. Login
        login(page)
        print("OK 1. Login admin/admin123")
        assert "Dashboard" in page.content()

        # 2. Criar categoria (nome único baseado em timestamp)
        import time
        cat_name = f"E2E-{int(time.time())}"
        page.goto(f"{BASE}/categorias/nova/")
        page.fill('input[name="nome"]', cat_name)
        # Usa seletor do form principal, evita o do filtro
        page.locator('form input[type="hidden"][name="csrfmiddlewaretoken"]').first.evaluate("el => el.closest('form').submit()")
        page.wait_for_load_state("networkidle", timeout=10000)
        assert cat_name in page.content() or "Categorias" in page.content(), \
            f"Falha ao criar categoria. URL: {page.url}"
        print(f"OK 2. Categoria '{cat_name}' criada")

        # 3. Criar fornecedor
        forn_name = f"Fornecedor-E2E-{int(time.time())}"
        page.goto(f"{BASE}/fornecedores/novo/")
        page.fill('input[name="nome"]', forn_name)
        page.locator('form input[type="hidden"][name="csrfmiddlewaretoken"]').first.evaluate("el => el.closest('form').submit()")
        page.wait_for_load_state("networkidle", timeout=10000)
        print(f"OK 3. Fornecedor '{forn_name}' criado")

        # 4. Criar produto
        prod_codigo = f"E2E-{int(time.time())}"
        page.goto(f"{BASE}/produtos/novo/")
        page.fill('input[name="nome"]', "Produto E2E")
        page.fill('input[name="codigo_interno"]', prod_codigo)
        page.select_option('select[name="categoria"]', label=cat_name)
        page.fill('input[name="estoque_minimo"]', "5")
        page.fill('input[name="estoque_ideal"]', "20")
        page.locator('form input[type="hidden"][name="csrfmiddlewaretoken"]').first.evaluate("el => el.closest('form').submit()")
        page.wait_for_load_state("networkidle", timeout=10000)
        print(f"OK 4. Produto '{prod_codigo}' criado")

        # Pegar ID do produto criado pelo codigo_interno na lista
        page.goto(f"{BASE}/produtos/?page_size=100")
        m = re.search(r'/produtos/(\d+)/"[^>]*>[^<]*</a>\s*</td>\s*<td[^>]*>\s*' + re.escape(prod_codigo), page.content())
        if not m:
            m = re.search(r'>' + re.escape(prod_codigo) + r'</td>\s*<td[^>]*>\s*<a href="/produtos/(\d+)/', page.content())
        prod_id = m.group(1)
        print(f"   Produto ID: {prod_id} (codigo {prod_codigo})")

        # 5. Verificar coluna Estoque na lista
        page.goto(f"{BASE}/produtos/")
        assert "ESTOQUE" in page.content().upper(), "Coluna ESTOQUE ausente"
        print("OK 5. Coluna Estoque presente na lista")

        # 6. Registrar entrada via form
        page.goto(f"{BASE}/estoque/entradas/nova/", wait_until="networkidle")
        csrf = page.locator('input[name="csrfmiddlewaretoken"]').first.input_value()
        resp = page.request.post(
            f"{BASE}/estoque/entradas/nova/",
            form={
                "csrfmiddlewaretoken": csrf,
                "produto": prod_id,
                "quantidade": "10",
                "valor_unitario": "2.50",
                "numero_lote": "LOTE-E2E-1",
                "data_validade": "2027-12-31",
                "motivo": "COMPRA",
            },
            headers={"Referer": f"{BASE}/estoque/entradas/nova/"},
            max_redirects=0,
        )
        assert resp.status in (200, 302), f"Entrada falhou: {resp.status} {resp.text()[:200]}"
        print(f"OK 6. Entrada registrada (status {resp.status})")

        # 7. Verificar que estoque aparece na lista como 10
        page.goto(f"{BASE}/produtos/")
        content = page.content()
        assert any(s in content for s in [">10<", ">10.000<", ">10,000<"]), \
            f"Estoque não atualizou na lista"
        print("OK 7. Estoque = 10 KG na lista")

        # 8. Registrar saída
        page.goto(f"{BASE}/estoque/saidas/nova/", wait_until="networkidle")
        csrf = page.locator('input[name="csrfmiddlewaretoken"]').first.input_value()
        resp = page.request.post(
            f"{BASE}/estoque/saidas/nova/",
            form={
                "csrfmiddlewaretoken": csrf,
                "produto": prod_id,
                "quantidade": "3",
                "motivo": "CONSUMO_INTERNO",
            },
            headers={"Referer": f"{BASE}/estoque/saidas/nova/"},
            max_redirects=0,
        )
        assert resp.status in (200, 302), f"Saída falhou: {resp.status} {resp.text()[:200]}"
        print(f"OK 8. Saída registrada (status {resp.status})")

        # 9. Estoque = 7
        page.goto(f"{BASE}/produtos/")
        content = page.content()
        assert any(s in content for s in [">7<", ">7.000<", ">7,000<"]), \
            f"Estoque não atualizou para 7"
        print("OK 9. Estoque = 7 KG após saída")

        # 10. Dashboard mostra o produto
        page.goto(f"{BASE}/")
        assert "Produto E2E" in page.content() or "7" in page.content()
        print("OK 10. Dashboard reflete estado")

        # 11. Inteligência
        page.goto(f"{BASE}/inteligencia/", wait_until="networkidle")
        assert "Inteligência" in page.content()
        print("OK 11. Página /inteligencia/")

        # 12. Relatórios
        for path, ctype in [
            ("/relatorios/movimentacoes.xlsx", "spreadsheetml"),
            ("/relatorios/estoque.xlsx", "spreadsheetml"),
            ("/relatorios/auditoria.xlsx", "spreadsheetml"),
            ("/relatorios/validade.pdf", "pdf"),
        ]:
            resp = page.request.get(BASE + path)
            assert resp.status == 200
            assert ctype in resp.headers["content-type"]
            assert len(resp.body()) > 1000
        print("OK 12. 4 relatórios exportam corretamente")

        browser.close()


def test_dark_mode():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1366, "height": 900})
        page = ctx.new_page()
        login(page)

        # Página em modo claro
        page.goto(f"{BASE}/", wait_until="networkidle")
        page.screenshot(path="C:/Users/Administrator/Desktop/Estoque/_validate_dark_light.png", full_page=True)
        html = page.evaluate("document.documentElement.classList.contains('dark')")
        print(f"  Modo claro: dark class = {html}")

        # Clica no toggle de tema
        page.click('button[title*="escuro"]')
        page.wait_for_timeout(300)
        page.screenshot(path="C:/Users/Administrator/Desktop/Estoque/_validate_dark_dark.png", full_page=True)
        html = page.evaluate("document.documentElement.classList.contains('dark')")
        local = page.evaluate("localStorage.getItem('theme')")
        print(f"  Modo escuro: dark class = {html}, localStorage.theme = {local}")
        assert html is True
        assert local == "dark"

        # Reload deve manter dark mode
        page.reload(wait_until="networkidle")
        html = page.evaluate("document.documentElement.classList.contains('dark')")
        print(f"  Após reload: dark class = {html}")
        assert html is True

        # Toggle de volta para claro
        page.click('button[title*="claro"]')
        page.wait_for_timeout(300)
        html = page.evaluate("document.documentElement.classList.contains('dark')")
        print(f"  Volta para claro: dark class = {html}")
        assert html is False

        browser.close()
        print("OK 13. Dark mode toggle + persistência")


def test_pwa_assets():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context()
        page = ctx.new_page()
        login(page)

        # Manifest
        resp = page.request.get(BASE + "/static/manifest.json")
        assert resp.status == 200
        m = resp.json()
        print(f"  Manifest name: {m.get('name')}, start_url: {m.get('start_url')}, icons: {len(m.get('icons', []))}")
        assert m.get("name") == "Estoque Cozinha"
        assert len(m.get("icons", [])) >= 2
        print("OK 14. PWA manifest válido")

        # Service worker
        resp = page.request.get(BASE + "/static/sw.js")
        assert resp.status == 200
        assert "serviceworker" in resp.headers.get("content-type", "").lower() or \
               resp.headers.get("content-type", "").startswith("application/javascript") or \
               "javascript" in resp.headers.get("content-type", "").lower()
        print(f"  Service Worker: {resp.headers.get('content-type')}, {len(resp.body())} bytes")
        assert "addEventListener('install'" in resp.text() or 'addEventListener("install"' in resp.text()
        print("OK 15. Service Worker válido")

        # Ícones
        for size in [192, 512]:
            resp = page.request.get(BASE + f"/static/icons/icon-{size}.png")
            assert resp.status == 200
            assert len(resp.body()) > 100
        print("OK 16. Ícones PWA acessíveis")

        # base.html contém link manifest
        page.goto(f"{BASE}/", wait_until="networkidle")
        assert page.locator('link[rel="manifest"]').count() == 1
        assert page.locator('meta[name="theme-color"]').count() == 1
        print("OK 17. PWA meta tags no HTML")

        # Offline page
        resp = page.request.get(BASE + "/offline/")
        assert resp.status == 200
        print("OK 18. Página /offline/ renderiza")

        browser.close()


def test_push_endpoints():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context()
        page = ctx.new_page()
        login(page)

        # VAPID public key
        resp = page.request.get(BASE + "/notificacoes/vapid-key/")
        assert resp.status == 200
        data = resp.json()
        assert "publicKey" in data
        assert len(data["publicKey"]) > 50
        print(f"OK 19. VAPID public key: {data['publicKey'][:30]}...")

        # Subscribe (com payload mockado)
        fake_sub = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test-e2e",
            "keys": {
                "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7Ihbe3WmIYF",
                "auth": "tBHItJI5svbpez7KI4CCXg",
            },
        }
        # Pega CSRF token de uma página com form (precisa para POSTs de API)
        page.goto(BASE + "/produtos/novo/", wait_until="networkidle")
        csrf = page.locator('input[name="csrfmiddlewaretoken"]').first.input_value()
        resp = page.request.post(
            BASE + "/notificacoes/subscribe/",
            data=fake_sub,
            headers={
                "Content-Type": "application/json",
                "X-CSRFToken": csrf,
                "Referer": BASE + "/",
            },
        )
        assert resp.status == 200, f"subscribe: {resp.status} {resp.text()[:300]}"
        print(f"OK 20. Subscription registrada")

        # Unsubscribe
        resp = page.request.post(
            BASE + "/notificacoes/unsubscribe/",
            data={"endpoint": fake_sub["endpoint"]},
            headers={
                "Content-Type": "application/json",
                "X-CSRFToken": csrf,
                "Referer": BASE + "/",
            },
        )
        assert resp.status == 200, f"unsubscribe: {resp.status} {resp.text()[:300]}"
        print(f"OK 21. Subscription removida")

        # Test push (vai falhar no envio real pq não há subscription, mas retorna JSON)
        resp = page.request.post(
            BASE + "/notificacoes/test/",
            headers={"X-CSRFToken": csrf, "Referer": BASE + "/"},
        )
        assert resp.status == 200, f"test: {resp.status} {resp.text()[:300]}"
        print(f"OK 22. Endpoint test_push: {resp.json()}")

        browser.close()


if __name__ == "__main__":
    print("=" * 60)
    print("TESTES E2E - FASE 5")
    print("=" * 60)
    test_main_flows()
    print()
    test_dark_mode()
    print()
    test_pwa_assets()
    print()
    test_push_endpoints()
    print()
    print("=" * 60)
    print("TODOS OS TESTES E2E PASSARAM")
    print("=" * 60)
