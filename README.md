# Estoque Cozinha Industrial

Sistema de gestão de estoque para cozinha industrial / restaurante corporativo.

Elimina problemas de falta de produtos, excesso de estoque, desperdícios, vencimentos e compras mal planejadas através de **regras de negócio, cálculos automáticos e histórico de movimentações**.

> **Status:** Todas as 5 fases entregues.
> Fases: Fundação → Movimentações → Inteligência → Dashboard/Relatórios → Polimento (PWA, dark mode, push, PostgreSQL, E2E).

---

## Stack

- **Python 3.11+** + **Django 5.x**
- **SQLite** (dev) / **PostgreSQL** (prod, via `DATABASE_URL`)
- **Tailwind CSS 3.4** (compilado via npm) + **Alpine.js** para interatividade
- **@tailwindcss/forms** para estilos consistentes de formulário
- **WhiteNoise** para servir estáticos em produção
- **django-widget-tweaks** para formulários
- **openpyxl** + **xhtml2pdf** para relatórios XLSX/PDF
- **pywebpush** + **py_vapid** para notificações Web Push
- **PWA** (Service Worker, manifest, installable, offline fallback)
- **Playwright** (E2E tests)

## Estrutura

```
estoque/
├── manage.py
├── requirements.txt
├── .env.example
├── setup.bat / start.bat / backup.bat / build-css.bat
├── estoque/                # Configurações do projeto
├── core/                   # Categoria, Fornecedor, Produto, Configuração
├── accounts/               # Autenticação, usuários, preferências
├── stock/                  # Lote, Movimento, Alerta, services
├── intelligence/           # Análises (consumo, ruptura, validade)
├── audit/                  # Logs imutáveis de auditoria
├── reports/                # Exports XLSX/PDF
├── notifications/          # VAPID + Web Push subscriptions
├── templates/              # Templates Django (server-rendered)
└── static/                 # CSS, JS, manifest, sw.js, icons
```

## Instalação (Windows)

### 1. Pré-requisitos
- **Python 3.11 ou superior** — [python.org/downloads](https://www.python.org/downloads/)
  - Na instalação marque **"Add Python to PATH"**
- **Node.js 18+** (para compilar Tailwind)

### 2. Instalação automática
Duplo-clique em **`setup.bat`** (ou execute no terminal):
```cmd
setup.bat
```
O script:
1. Cria o ambiente virtual `.venv`
2. Instala dependências Python (incluindo `psycopg[binary]` para PostgreSQL)
3. Instala dependências Node (Tailwind) e compila o CSS
4. Copia `.env.example` para `.env`
5. Detecta SQLite (padrão) ou PostgreSQL (se `DATABASE_URL` apontar para `postgres://`)
6. Aplica as migrações
7. Cria o superusuário `admin/admin123` (se não existir)
8. Inicia o servidor em `http://127.0.0.1:8000`

### 3. Instalação manual
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
npm install
npm run build:css
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Acesse:
- Sistema: http://127.0.0.1:8000
- Admin Django: http://127.0.0.1:8000/admin
- Login padrão dev: `admin` / `admin123`

### 4. Desenvolvimento do CSS (Tailwind)
Para que mudanças em classes Tailwind sejam aplicadas:
```cmd
npm run build:css          # build único
npm run watch:css          # watch automático
```

Em Windows:
```cmd
build-css.bat              # build único
```

## Configuração (.env)

```ini
DEBUG=True
SECRET_KEY=sua-chave-secreta-aqui
ALLOWED_HOSTS=127.0.0.1,localhost,0.0.0.0,testserver

# Banco: SQLite (padrão) ou PostgreSQL
DATABASE_URL=postgres://usuario:senha@localhost:5432/estoque

# VAPID (gerado automaticamente na primeira execução, persistir em prod)
VAPID_PRIVATE_KEY=
VAPID_PUBLIC_KEY=
VAPID_CLAIMS_SUB=mailto:admin@estoque.local
```

### Migração para PostgreSQL
1. Instale PostgreSQL 12+ e crie um banco
2. Defina `DATABASE_URL=postgres://user:pass@host:5432/dbname` no `.env`
3. Reexecute `setup.bat` (ou `pip install -r requirements.txt` + `python manage.py migrate`)

O sistema detecta automaticamente via `dj_database_url` e troca o engine para `postgresql` (psycopg v3).

## Backup

Execute **`backup.bat`** (auto-detecta banco):

- **SQLite**: copia `db.sqlite3` para `backups/db-AAAAMMDD_HHMMSS.sqlite3`
- **PostgreSQL**: extrai nome do banco do `DATABASE_URL` e roda `pg_dump` para `backups/estoque-AAAAMMDD_HHMMSS.sql`

Agende no Windows Task Scheduler para backups diários.

## Recursos

### Movimentações de estoque
- **Entrada** com lote, validade, valor unitário, fornecedor e nota fiscal
- **Saída** com FEFO automático (consome do lote que vence primeiro)
- **Ajuste** de inventário (adição/remoção com justificativa)
- **Cancelamento** de movimento (reverte saldo, mantém histórico)
- **Valor médio** e custo total em tempo real

### Inteligência
- Consumo médio (diário, semanal, mensal)
- Data estimada de ruptura
- Sugestões de compra (baseadas em estoque ideal)
- Detecção de consumo anormal
- Identificação de produtos em excesso / parados

### Dashboard e Relatórios
- Dashboard gerencial com KPIs e seletor de período (configurável por usuário)
- Gráfico "Dias de cobertura" (cores por faixa: vermelho ≤7 / amarelo 8-15 / verde 16-30 / azul >30)
- Exportações:
  - **Movimentações** (XLSX)
  - **Posição de estoque** (XLSX, com aba de lotes)
  - **Auditoria** (XLSX)
  - **Validade** (PDF, com faixas: Vencidos / Crítico / Alerta / Atenção / OK)

### PWA (Progressive Web App)
- **Instalável** como app no celular/desktop
- **Offline fallback** (`/offline/`)
- **Service Worker** com cache + handlers de push
- **Manifest** completo (ícones 192/512 + maskable, theme color, standalone)

### Dark Mode
- Toggle no header (lua/sol)
- Persiste em `localStorage.theme` (fallback `prefers-color-scheme`)
- Aplica classe `dark` no `<html>` antes do Alpine (sem FOUC)

### Notificações Push
- Endpoint `GET /notificacoes/vapid-key/` retorna chave pública
- `POST /notificacoes/subscribe/` registra subscription
- `POST /notificacoes/unsubscribe/` remove
- `POST /notificacoes/test/` envia push de teste
- Service Worker exibe notificações e abre URL no clique

## Testes

### Unit tests (Django)
```cmd
python manage.py test
```
- **68 testes** cobrindo stock, intelligence, reports, core, accounts

### E2E tests (Playwright)
```cmd
playwright install chromium
python tests_e2e_fase5.py
```
- **22 testes E2E** cobrindo fluxos principais, dark mode, PWA assets, push endpoints

## Acesso via rede local / produção

```cmd
# Dev
python manage.py runserver 0.0.0.0:8000

# Prod (Linux)
pip install gunicorn
gunicorn estoque.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

## Roadmap

- [x] **Fase 1** — Fundação (modelos, auth, CRUDs, auditoria)
- [x] **Fase 2** — Movimentações (entrada/saída/ajuste, FEFO, valor médio)
- [x] **Fase 3** — Inteligência (consumo, ruptura, sugestões, anomalias)
- [x] **Fase 4** — Dashboard gerencial + relatórios XLSX/PDF
- [x] **Fase 5** — Polimento (PWA, dark mode, push, PostgreSQL, E2E)

## Suporte

Problemas ou dúvidas: abra uma issue ou contate o administrador do sistema.
