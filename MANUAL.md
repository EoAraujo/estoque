# Manual Completo — Estoque Cozinha Industrial

> **Para quem é este manual:** administrador do sistema, equipe de TI da cozinha, devs que farão manutenção, gestor que precisa entender o que o sistema faz.

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Stack técnica](#2-stack-técnica)
3. [Pré-requisitos](#3-pré-requisitos)
4. [Instalação completa](#4-instalação-completa)
5. [Configuração (.env)](#5-configuração-env)
6. [Banco de dados: SQLite vs PostgreSQL](#6-banco-de-dados-sqlite-vs-postgresql)
7. [Estrutura do projeto](#7-estrutura-do-projeto)
8. [URLs e navegação](#8-urls-e-navegação)
9. [Modelo de dados](#9-modelo-de-dados)
10. [Como usar: fluxo do dia a dia](#10-como-usar-fluxo-do-dia-a-dia)
11. [Funcionalidades em detalhe](#11-funcionalidades-em-detalhe)
12. [Backup e restore](#12-backup-e-restore)
13. [Testes automatizados](#13-testes-automatizados)
14. [Desenvolvimento (manutenção)](#14-desenvolvimento-manutenção)
15. [Deploy em produção](#15-deploy-em-produção)
16. [Segurança e boas práticas](#16-segurança-e-boas-práticas)
17. [Troubleshooting](#17-troubleshooting)
18. [Glossário](#18-glossário)

---

## 1. Visão geral

**Estoque Cozinha Industrial** é um sistema web para controlar estoque de cozinha industrial / restaurante corporativo. Resolve os problemas clássicos:

- **Falta de produtos** no momento do preparo
- **Excesso de estoque** (capital parado + risco de vencimento)
- **Desperdício** por validade vencida
- **Compras mal planejadas** (sem base histórica)
- **Perda de rastreabilidade** (quem mexeu, quando, por quê)

**Como resolve:** regras de negócio + cálculos automáticos + histórico imutável de movimentações. Sem dependência de IA externa.

**Entregue em 5 fases:**

| Fase | Nome        | O que entrega                                                                                   |
|------|-------------|-------------------------------------------------------------------------------------------------|
| 1    | Fundação    | Modelos, autenticação, CRUDs de Categoria/Fornecedor/Produto/Usuário, auditoria automática    |
| 2    | Movimentações | Entrada/saída/ajuste de estoque, controle de lote/validade, FEFO, valor médio, cancelamento  |
| 3    | Inteligência | Consumo médio, ruptura iminente, sugestões de compra, anomalias, excesso, parados            |
| 4    | Dashboard   | Painel gerencial com KPIs + gráfico "Dias de cobertura" + 4 relatórios exportáveis (XLSX/PDF) |
| 5    | Polimento   | PWA instalável, dark mode, notificações Web Push, suporte PostgreSQL, testes E2E Playwright   |

---

## 2. Stack técnica

**Backend**
- Python 3.11+
- Django 5.0 (apps: `core`, `accounts`, `stock`, `intelligence`, `audit`, `reports`, `notifications`)
- WhiteNoise (estáticos em prod)
- django-widget-tweaks (formulários)
- python-dotenv (carrega `.env`)

**Banco**
- **Dev:** SQLite (arquivo único, zero config)
- **Prod:** PostgreSQL 12+ (psycopg v3)
- `dj-database-url` faz a troca automática via `DATABASE_URL`

**Frontend**
- Tailwind CSS 3.4 **compilado via npm** (não usa Play CDN — evita FOUC)
- `@tailwindcss/forms`
- Alpine.js 3.13 (interatividade leve: sidebar mobile, dropdown, dark mode)
- Chart.js 4.4 (gráfico de cobertura)
- PWA: manifest + service worker + ícones 192/512 + maskable
- Dark mode via classe `dark` no `<html>` (ativado antes do Alpine para evitar flash)

**Relatórios**
- openpyxl 3.1+ (XLSX)
- xhtml2pdf 0.2+ (PDF)

**Notificações push**
- pywebpush 2.0+ (cliente VAPID)
- py-vapid 2.0+ (geração de chaves)
- cryptography 41+ (extração de chave pública)

**Testes**
- Django `manage.py test` (unit/integration, SQLite isolado)
- Playwright (E2E com Chromium)

---

## 3. Pré-requisitos

| Recurso | Mínimo | Recomendado | Onde obter |
|---------|--------|-------------|------------|
| Python  | 3.11   | 3.12        | https://python.org/downloads/ |
| Node.js | 18 LTS | 20 LTS      | https://nodejs.org/ |
| pip     | 24     | 25+         | incluído no Python |
| SO      | Windows 10/11 ou Linux com bash | — | — |
| RAM     | 2 GB   | 4 GB+       | depende do tamanho do estoque |
| Disco   | 500 MB | 5 GB+       | para backup local |

**Em produção, adicional:**
- PostgreSQL 12+ (ou um container Docker)
- Servidor WSGI: `gunicorn` (Linux) ou `waitress` (Windows)
- Proxy reverso: nginx (Linux) ou IIS (Windows)
- HTTPS válido (Let's Encrypt)

---

## 4. Instalação completa

### 4.1 Instalação automática (Windows)

1. Instale Python 3.11+ (marque **"Add Python to PATH"** na instalação).
2. Instale Node.js 18+.
3. Copie a pasta do projeto para o destino final (ex: `C:\Estoque`).
4. Abra o terminal na pasta do projeto e execute:

   ```cmd
   setup.bat
   ```

O `setup.bat` faz, em ordem:
1. Detecta Python
2. Cria `.venv` (ambiente virtual)
3. Instala dependências Python (`pip install -r requirements.txt`)
4. Instala dependências Node (`npm install`) e compila Tailwind (`npx tailwindcss ...`)
5. Copia `.env.example` para `.env` (se não existir)
6. Detecta se `DATABASE_URL` aponta para `postgres://` (e mostra na tela)
7. Aplica as migrações (`manage.py migrate`)
8. Cria o superusuário `admin` / `admin123` (se não existir)
9. Pergunta se quer iniciar o servidor agora

### 4.2 Instalação manual (qualquer SO)

```bash
git clone <repo> estoque && cd estoque
python -m venv .venv

# Linux/Mac:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (cmd):
.venv\Scripts\activate.bat

pip install -r requirements.txt
npm install
npm run build:css
cp .env.example .env          # Linux/Mac
copy .env.example .env        # Windows

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

### 4.3 Verificação pós-instalação

Acesse:
- **App:** http://127.0.0.1:8000
- **Admin Django:** http://127.0.0.1:8000/admin

Login padrão dev: `admin` / `admin123` (criado pelo `setup.bat`).

### 4.4 Compilação do CSS em modo dev

Toda vez que você adicionar/alterar classes Tailwind em templates, recompile:

```bash
npm run build:css     # build único
npm run watch:css     # watch automático (recompila ao salvar)
```

Em Windows você também tem `build-css.bat`.

> **Importante:** o `tailwind.config.js` lista os diretórios que ele escaneia para encontrar classes. Se você criar um novo app/templates, **adicione o path ao `content`**.

---

## 5. Configuração (.env)

Crie/edite o arquivo `.env` na raiz do projeto:

```ini
# Chave secreta - GERAR UMA NOVA EM PRODUÇÃO
#   python -c "import secrets; print(secrets.token_urlsafe(50))"
SECRET_KEY=troque-por-uma-chave-segura-em-producao
DEBUG=False
ALLOWED_HOSTS=estoque.exemplo.com,127.0.0.1,localhost

# Banco - SQLite (padrão, dev) ou PostgreSQL (prod)
# Vazio = SQLite em db.sqlite3
# DATABASE_URL=postgres://usuario:senha@host:5432/banco
DATABASE_URL=

# VAPID (Web Push) - gerado em runtime, persistir em prod
VAPID_PRIVATE_KEY=
VAPID_PUBLIC_KEY=
VAPID_CLAIMS_SUB=mailto:admin@estoque.local
```

**Como gerar chaves VAPID em produção:**

```bash
python -c "from py_vapid import Vapid02; v=Vapid02(); v.generate_keys(); print('PRIV:'); print(v.private_pem().decode())"
python -c "from py_vapid import Vapid02; v=Vapid02(); v.generate_keys(); from cryptography.hazmat.primitives import serialization; import base64; raw=v._public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint); print('PUB:'); print(base64.urlsafe_b64encode(raw).rstrip(b'=').decode())"
```

Cole as chaves no `.env`. **Sem VAPID em prod, push notifications não funcionam**, mas o resto do sistema segue OK.

---

## 6. Banco de dados: SQLite vs PostgreSQL

### Quando usar cada um

| Critério | SQLite | PostgreSQL |
|----------|--------|------------|
| Instalação | Zero (arquivo único) | Requer servidor |
| Múltiplos usuários simultâneos | Fraco | Forte |
| Volume de dados | Até ~100k movimentos | Ilimitado |
| Backup | Copiar `db.sqlite3` | `pg_dump` |
| Indicado para | 1–3 usuários, cozinha pequena/média | Múltiplos setores, produção real |

### Como o sistema decide

`estoque/settings.py:88-95`:

```python
db_url = os.environ.get("DATABASE_URL")
if db_url and (db_url.startswith("postgres://") or db_url.startswith("postgresql://")):
    import dj_database_url
    DATABASES["default"] = dj_database_url.parse(
        db_url, conn_max_age=600, conn_health_checks=True,
    )
    DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"
```

Ou seja: **se `DATABASE_URL` começa com `postgres://` ou `postgresql://`, troca automaticamente**. Caso contrário, usa SQLite.

### Migração SQLite → PostgreSQL

1. Instale PostgreSQL e crie o banco:
   ```sql
   CREATE DATABASE estoque OWNER estoque_user;
   ```
2. Instale `psycopg[binary]` (já está em `requirements.txt`).
3. Edite `.env`:
   ```ini
   DATABASE_URL=postgres://estoque_user:senha@localhost:5432/estoque
   ```
4. Exporte os dados do SQLite:
   ```bash
   python manage.py dumpdata --exclude auth.permission --exclude contenttypes --indent 2 > dump.json
   ```
5. Aponte para o PostgreSQL e importe:
   ```bash
   python manage.py migrate
   python manage.py loaddata dump.json
   ```

---

## 7. Estrutura do projeto

```
estoque/
├── manage.py
├── requirements.txt
├── .env.example
├── .env                          # criado pelo setup, NÃO versionar
├── db.sqlite3                    # banco dev (se SQLite)
├── setup.bat / start.bat / backup.bat / build-css.bat
├── package.json / package-lock.json
├── tailwind.config.js
│
├── estoque/                      # configurações do Django
│   ├── settings.py               # INSTALLED_APPS, MIDDLEWARE, DATABASES, VAPID
│   ├── urls.py                   # roteador raiz
│   ├── wsgi.py / asgi.py
│
├── core/                         # cadastros-base
│   ├── models.py                 # Categoria, Fornecedor, Produto, ConfiguracaoSingleton
│   ├── views.py                  # dashboard, CRUDs
│   ├── urls.py
│   ├── forms.py / admin.py / tests.py
│   ├── context_processors.py
│
├── accounts/                     # usuários
│   ├── models.py                 # UserProfile (periodo_padrao, dark_mode, push_enabled)
│   ├── views.py                  # login/logout, CRUD usuários, preferências
│   ├── urls.py
│
├── stock/                        # movimentações
│   ├── models.py                 # Lote, Movimento, Alerta
│   ├── services.py               # registrar_entrada/saida/ajuste, FEFO, valor médio
│   ├── forms.py                  # EntradaForm, SaidaForm, AjusteForm, CancelarMovimentoForm
│   ├── views.py                  # dashboards e CRUDs
│   ├── urls.py
│
├── intelligence/                 # cálculos preditivos
│   ├── analises.py               # consumo_medio, dias_restantes, sugestoes_compra, etc
│   ├── views.py                  # página única /inteligencia/
│   ├── urls.py
│
├── audit/                        # log de auditoria
│   ├── models.py                 # LogAuditoria (imutável)
│   ├── middleware.py             # expõe request ao signals
│   ├── signals.py                # post_save/post_delete de CRUDs + login/logout
│   ├── views.py                  # lista de logs
│
├── reports/                      # exports
│   ├── views.py                  # 4 views: XLSX movimentações, XLSX estoque, XLSX auditoria, PDF validade
│   ├── utils.py                  # helpers para formatação
│
├── notifications/                # Web Push
│   ├── models.py                 # WebPushSubscription
│   ├── views.py                  # vapid_public_key, subscribe, unsubscribe, test_push
│   ├── vapid.py                  # geração de chaves VAPID
│
├── templates/                    # Django templates (server-rendered)
│   ├── base.html                 # layout principal: sidebar + header + dark mode + push + SW
│   ├── dashboard.html
│   ├── offline.html              # fallback PWA
│   ├── accounts/
│   ├── audit/
│   ├── core/
│   ├── intelligence/
│   ├── registration/login.html
│   └── stock/
│
├── static/
│   ├── manifest.json             # PWA
│   ├── sw.js                     # service worker
│   ├── icons/                    # 192/512 + maskable
│   ├── css/app.css               # Tailwind compilado
│   └── src/input.css             # fonte do Tailwind
│
└── tests_e2e_fase5.py            # 22 testes E2E Playwright
```

---

## 8. URLs e navegação

### Rotas principais

| URL                          | O que faz                                          | Quem acessa |
|------------------------------|----------------------------------------------------|-------------|
| `/`                          | Dashboard (KPIs, gráfico, ações, relatórios)      | Todos       |
| `/produtos/`                 | Lista de produtos (com coluna Estoque)             | Todos       |
| `/produtos/novo/`            | Cadastrar produto                                  | Todos       |
| `/produtos/<id>/`            | Detalhe + histórico de movimentações               | Todos       |
| `/produtos/<id>/editar/`     | Editar                                             | Todos       |
| `/categorias/`, `/fornecedores/` | CRUD                                          | Todos       |
| `/configuracoes/`            | Configurações globais (CNPJ, janelas de alerta)    | Staff       |
| `/estoque/`                  | Painel de movimentações (entradas, saídas, ajustes)| Todos       |
| `/estoque/entradas/nova/`    | Formulário de entrada (lote, validade, valor)      | Todos       |
| `/estoque/saidas/nova/`      | Formulário de saída (FEFO automático)              | Todos       |
| `/estoque/ajustes/novo/`     | Formulário de ajuste de inventário                 | Todos       |
| `/estoque/movimentacoes/`    | Histórico filtrável                                | Todos       |
| `/estoque/movimentacoes/<id>/` | Detalhe de uma movimentação                     | Todos       |
| `/estoque/movimentacoes/<id>/cancelar/` | Cancelar (com justificativa)            | Staff       |
| `/inteligencia/`             | Página única com 5 seções (ruptura, sugestões, anomalias, baixo, excesso) | Todos |
| `/usuarios/`                 | Lista de usuários                                  | Staff       |
| `/usuarios/novo/`            | Cadastrar usuário                                  | Staff       |
| `/usuarios/<id>/senha/`      | Redefinir senha                                    | Staff       |
| `/preferencias/`             | Período padrão do dashboard, dark mode, push        | O próprio   |
| `/auditoria/`                | Log imutável de todas as ações                     | Staff       |
| `/relatorios/movimentacoes.xlsx` | Exportar movimentações do período             | Todos       |
| `/relatorios/estoque.xlsx`   | Posição de estoque + lotes                         | Todos       |
| `/relatorios/validade.pdf`   | Lotes por faixa de vencimento (PDF colorido)       | Todos       |
| `/relatorios/auditoria.xlsx` | Log de auditoria do período                        | Staff       |
| `/notificacoes/vapid-key/`   | GET: retorna chave pública VAPID                    | API         |
| `/notificacoes/subscribe/`   | POST: registra subscription                        | API         |
| `/notificacoes/unsubscribe/` | POST: remove subscription                          | API         |
| `/notificacoes/test/`        | POST: envia push de teste                          | API         |
| `/offline/`                  | Página de fallback (PWA)                           | Público     |
| `/admin/`                    | Admin nativo do Django                             | Superuser   |
| `/contas/login/`, `/contas/logout/` | Autenticação                                | Público     |

### Sidebar (menu lateral)

```
┌─ Estoque Cozinha ───────────┐
│ ● EC   Sistema              │
├─────────────────────────────┤
│ 📊 Dashboard                │
├─ Cadastros ─────────────────┤
│ 📦 Produtos                 │
│ 🏷  Categorias              │
│ 🏢 Fornecedores             │
├─ Operação ──────────────────┤
│ 🔄 Movimentações            │
│ 🎯 Inteligência            │
│ ⏰ Período                  │
├─ Administração (staff) ─────┤
│ 👥 Usuários                 │
│ 📋 Auditoria                │
│ ⚙  Configurações            │
├─────────────────────────────┤
│ 🚪 Sair                     │
└─────────────────────────────┘
```

---

## 9. Modelo de dados

### 9.1 Diagrama lógico (resumido)

```
TimeStampedModel (abstrata)
   ├── Categoria
   │      ↑ 1:N
   ├── Fornecedor
   │      ↑ 1:N
   └── Produto  ──────► UserProfile
           ↑ 1:N
        Lote ─── (FK) ──► Movimento ─── (FK) ──► User (created_by/updated_by)
                                       │
                                       └── (FK) ──► Lote
                                       └── (FK) ──► Fornecedor
                                       └── (FK) ──► Produto
                                       └── (cancelado, motivo_cancelamento, ...)

Alerta    (gerado por intelligence.gerar_alertas, ainda não ativado)
LogAuditoria    (imutável, populado por signals)
WebPushSubscription    (FK User)
```

### 9.2 Tabelas principais

**`core_categoria`** — Categoria de produto
- `nome` (unique), `descricao`, `ativa`, `cor` (#RRGGBB para dashboard)

**`core_fornecedor`** — Fornecedor
- `nome`, `nome_fantasia`, `cnpj`, `contato_nome`, `telefone`, `email`, `endereço completo`, `lead_time_days`, `ativo`

**`core_produto`** — Produto
- `nome`, `codigo_interno` (unique), `codigo_barras`
- `categoria` (FK PROTECT), `fornecedor_principal` (FK SET_NULL)
- `unidade_medida` (KG/G/L/ML/UN/CX/PC/DZ/FD)
- `controla_validade` (boolean)
- `estoque_minimo`, `estoque_ideal` (decimal 12,3)
- `localizacao`, `observacoes`, `ativo`
- `quantidade_atual` (property: soma movimentos não cancelados)

**`stock_lote`** — Lote de um produto
- `produto` (FK), `numero_lote`, `data_fabricacao`, `data_validade`, `data_entrada`
- `quantidade_inicial`, `quantidade_atual` (decimal 12,3)
- `nota_fiscal`, `observacoes`, `ativo`
- `dias_para_vencer`, `vencido` (properties)

**`stock_movimento`** — **IMUTÁVEL**. Nunca deletado.
- `produto`, `lote` (opcional), `tipo` (ENTRADA/SAIDA), `motivo`
- `quantidade`, `valor_unitario`, `valor_total`, `fornecedor`, `nota_fiscal`
- `responsavel`, `data_movimento`, `observacoes`
- `cancelado` (bool), `motivo_cancelamento` (string)

**`audit_logauditoria`** — Log de auditoria
- `url`, `metodo`, `usuario`, `acao` (CRIAR/EDITAR/EXCLUIR/MOVER/CANCELAR/LOGIN/LOGOUT)
- `objeto_repr`, `dados` (JSON), `created_at`

**`accounts_userprofile`** — Preferências por usuário
- `user` (OneToOne), `periodo_padrao` (7/15/30/90/180/365)
- `dark_mode` (auto/light/dark), `push_enabled`

**`notifications_webpushsubscription`** — Subscription push
- `user` (FK), `endpoint` (unique URL), `p256dh`, `auth`, `user_agent`, `ativo`, timestamps

### 9.3 Regras de negócio críticas

- **Movimentos são imutáveis.** Para corrigir, registre um novo movimento (entrada/saída/ajuste) ou use "Cancelar" (que apenas marca `cancelado=True` e reverte o saldo).
- **Estoque = soma de movimentos não cancelados.** Não há campo `quantidade` no Produto; é uma `property` calculada.
- **Saídas consomem lotes em ordem FEFO** (First-Expire-First-Out): lote que vence primeiro é consumido primeiro. Você pode forçar um lote específico.
- **Valor médio** = média ponderada das entradas dos últimos 90 dias com `valor_unitario`.

---

## 10. Como usar: fluxo do dia a dia

### Dia 1 — Configuração inicial

1. **Login** com `admin` / `admin123`.
2. **Configurações globais** (`/configuracoes/`):
   - Preencha nome da empresa, CNPJ, telefone, endereço
   - Defina janelas de alerta de vencimento (padrão: 30/15/7/3 dias)
   - Defina janela de cálculo de consumo (padrão: 30 dias)
3. **Cadastre Categorias** (`/categorias/nova/`):
   - Ex: Hortifruti, Carnes, Laticínios, Limpeza, Secos
4. **Cadastre Fornecedores** (`/fornecedores/novo/`):
   - Nome, CNPJ, contato, **lead_time_days** (prazo de entrega)
5. **Cadastre Produtos** (`/produtos/novo/`):
   - Nome, código interno (único), código de barras (opcional)
   - Categoria, fornecedor principal, unidade de medida
   - **Estoque mínimo** (alvo de alerta) e **estoque ideal** (alvo de compra)
   - **Controla validade** = marcado (para alimentos)
   - Localização física (Prateleira, Câmara fria)
6. **Cadastre mais usuários** (`/usuarios/novo/`) — Operador, Conferente, Gerente, Admin.
   - Cada um com suas permissões (is_staff para ver admin e auditoria)
7. **Configure as preferências do admin** (`/preferencias/`):
   - Período padrão do dashboard (ex: 30 dias)
   - Ative dark mode se quiser
   - Ative notificações push (botão de sininho no header)

### Operação diária

**Manhã — Recebimento de mercadoria:**
1. Vá em **Movimentações → + Entrada** (`/estoque/entradas/nova/`).
2. Selecione o produto, informe a quantidade.
3. Preencha: número do lote, data de fabricação, **data de validade**, valor unitário, fornecedor, nota fiscal.
4. Escolha o motivo (normalmente **COMPRA**).
5. Clique em **Registrar**. O sistema cria o **Lote** automaticamente.
6. Veja o estoque atualizar no dashboard.

**Durante o dia — Consumos:**
1. Vá em **Movimentações → − Saída** (`/estoque/saidas/nova/`).
2. Selecione o produto, informe a quantidade.
3. **Lote (opcional):** deixe em branco para FEFO automático, ou escolha um lote específico.
4. Escolha o motivo (PRODUCAO, CONSUMO_INTERNO, PERDA, DESCARTE, VENCIMENTO).
5. Informe o responsável/setor (opcional).
6. Clique em **Registrar**.

**Fim do dia — Conferência:**
1. Abra o **Dashboard** (`/`):
   - Veja o valor total em estoque
   - Veja quantos produtos estão em estado crítico (≤7 dias de cobertura)
   - Veja o gráfico "Dias de cobertura" — barras vermelhas pedem ação imediata
2. Abra **Inteligência** (`/inteligencia/`):
   - **Ruptura iminente:** produtos que vão zerar em breve
   - **Sugestões de compra:** quanto comprar de cada
   - **Anomalias de consumo:** produtos com consumo muito acima/abaixo da média
   - **Estoque abaixo do mínimo:** alerta
   - **Excesso de estoque:** itens parados ou em quantidade muito acima do ideal
3. Exporte relatórios se necessário (botões no dashboard).

**Inventário mensal (recomendado):**
1. Conte fisicamente o estoque.
2. Para diferenças, vá em **Movimentações → ⚖ Ajuste** (`/estoque/ajustes/novo/`).
3. Escolha **Direção:** ENTRADA (sistema tinha menos) ou SAÍDA (sistema tinha mais).
4. Informe a quantidade e a justificativa (obrigatória).
5. O sistema registra o ajuste sem mexer no histórico.

### Quando algo dá errado

**"Errei a quantidade na última entrada"**
- Não edite. Vá em Movimentações → encontre o movimento → clique em **Cancelar** (staff) e registre a entrada correta.

**"Venceu um lote e o sistema ainda mostra estoque"**
- Registre uma **saída** com motivo **VENCIMENTO** sobre o lote específico.

**"O fornecedor entregou nota fiscal errada"**
- Cancele a entrada (reverte estoque) e registre novamente com a NF correta.

---

## 11. Funcionalidades em detalhe

### 11.1 Movimentações de estoque

**Entrada** (`/estoque/entradas/nova/`)
- Cria automaticamente um Lote com quantidade inicial = quantidade informada
- Se o produto `controla_validade`, a data de validade é obrigatória
- Registra valor unitário e calcula valor total
- Permite vincular fornecedor e nota fiscal
- Atualiza estoque do produto

**Saída** (`/estoque/saidas/nova/`)
- **FEFO por padrão:** se nenhum lote for escolhido, consome do lote que vence primeiro
- Você pode forçar um lote específico (ex: "estoque da Câmara 2")
- Motivos disponíveis: PRODUCAO, CONSUMO_INTERNO, DESCARTE, PERDA, TRANSFERENCIA_OUT, AJUSTE_SAIDA, VENCIMENTO, OUTRO_S
- Validação: bloqueia saída se `quantidade > estoque_atual`

**Ajuste** (`/estoque/ajustes/novo/`)
- Usado para corrigir divergências de inventário
- Requer justificativa (mínimo 10 caracteres)
- Direção: ENTRADA (adiciona) ou SAÍDA (remove)
- Para SAÍDA, é obrigatório selecionar o lote

**Cancelar** (`/estoque/movimentacoes/<id>/cancelar/`)
- Disponível apenas para staff
- Requer motivo de cancelamento (mínimo 10 caracteres)
- Marca o movimento como `cancelado=True` e reverte o saldo
- **Não deleta** o registro — fica no histórico para auditoria

### 11.2 Inteligência (`/inteligencia/`)

Página única com 5 seções:

1. **Ruptura iminente** — produtos cuja `data_estimada_ruptura` está nos próximos 7 dias
2. **Sugestões de compra** — `quantidade_recomendada = max(estoque_ideal - quantidade_atual, 0)` + fornecedor principal + lead time
3. **Anomalias de consumo** — produtos com consumo 50% acima ou abaixo da média histórica
4. **Estoque abaixo do mínimo** — `quantidade_atual <= estoque_minimo`
5. **Excesso de estoque** — `quantidade_atual > 2 * estoque_ideal` por mais de 30 dias sem movimento

Todos os cálculos usam **regras determinísticas** (sem IA). O `intelligence.analises` é um módulo puro Python — fácil de auditar e ajustar.

### 11.3 Dashboard (`/`)

- **4 KPIs:** Valor em estoque, Movs. no período, Estoque baixo, Vencendo/Vencidos
- **Seletor de período:** 7/15/30/90/180/365 dias (salvo em `UserProfile.periodo_padrao`)
- **Gráfico "Dias de cobertura":** Chart.js horizontal bar com cores:
  - 🔴 Vermelho: 0–7 dias (crítico)
  - 🟡 Amarelo: 8–15 dias (atenção)
  - 🟢 Verde: 16–30 dias (normal)
  - 🔵 Azul: >30 dias (excesso)
- **Ações rápidas:** links para entrada/saída/ajuste/inteligência
- **Painel de relatórios:** 4 botões de export
- **Últimas movimentações:** tabela com as 10 mais recentes
- **Estoque abaixo do mínimo:** lista lateral de produtos críticos

### 11.4 Relatórios

Todos gerados **on-the-fly** (sem armazenar arquivos):

| Relatório | URL | Formato | Conteúdo |
|-----------|-----|---------|----------|
| Movimentações | `/relatorios/movimentacoes.xlsx?periodo=30` | XLSX | Entradas e saídas com filtros |
| Posição de estoque | `/relatorios/estoque.xlsx` | XLSX (2 abas) | Produtos + Lotes ativos |
| Auditoria | `/relatorios/auditoria.xlsx?periodo=30` | XLSX | Log de ações (staff only) |
| Validade | `/relatorios/validade.pdf` | PDF | Lotes agrupados por faixa de vencimento (cores) |

### 11.5 PWA (Progressive Web App)

**Como instalar:**
- **Android/Chrome:** menu → "Instalar app" ou "Adicionar à tela inicial"
- **iOS/Safari:** botão de compartilhar → "Adicionar à Tela de Início"
- **Desktop (Chrome/Edge):** ícone de instalação na barra de endereço

**Recursos offline:**
- O Service Worker (`/static/sw.js`) faz cache de páginas e assets
- Quando offline, mostra a página `/offline/`
- Network-first com cache fallback (dados sempre frescos quando online)
- Não cacheia `/admin/` (sempre online)

### 11.6 Dark mode

- Toggle no header (ícone lua/sol)
- Persiste em `localStorage.theme` (chave: `'light'` ou `'dark'`)
- Aplica classe `dark` no `<html>` **antes do Alpine.js carregar** (script inline) — sem flash
- Fallback para `prefers-color-scheme` do SO
- Configurável também em `/preferencias/`

### 11.7 Notificações push (Web Push)

**Para o usuário ativar:**
1. Clique no ícone de sininho no header
2. O navegador pede permissão → aceita
3. A subscription é salva no servidor (`/notificacoes/subscribe/`)
4. O servidor pode enviar push via `notifications.services.enviar_para_usuario(usuario, titulo, body, url)`

**Casos de uso para implementar:**
- Estoque abaixo do mínimo de um produto crítico
- Lote vencendo em 3 dias
- Nova sugestão de compra
- Produto parado há muito tempo

**Funcionamento técnico:**
- O service worker (`/static/sw.js`) recebe `push` events e mostra `Notification`
- Ao clicar, abre a URL em uma janela/tab focada
- VAPID auth garante que só seu servidor pode enviar push

**Para testar manualmente:**
- Botão de sininho no header ativa/desativa
- Endpoint `POST /notificacoes/test/` envia um push de teste para o usuário logado

### 11.8 Auditoria

Todas as ações que alteram dados são registradas automaticamente em `audit.LogAuditoria`:

- **CRUDs** (CRIAR, EDITAR, EXCLUIR) em Categoria, Fornecedor, Produto, Usuário, Lote
- **Movimentações** (MOVER para entrada/saída/ajuste; CANCELAR)
- **Autenticação** (LOGIN, LOGOUT)

O log inclui: usuário, IP, método HTTP, URL, objeto afetado, timestamp, dados extras (JSON).

Acesse em `/auditoria/` (apenas staff).

---

## 12. Backup e restore

### 12.1 Backup automático

Execute `backup.bat` (auto-detecta o banco):

- **SQLite:** copia `db.sqlite3` para `backups/estoque-AAAA-MM-DD_HH-MM-SS.sqlite3`
- **PostgreSQL:** extrai nome do banco do `DATABASE_URL` e roda `pg_dump` → `backups/estoque-AAAA-MM-DD_HH-MM-SS-pg.sql`

### 12.2 Agendar no Windows

1. Abra o **Agendador de Tarefas** (`taskschd.msc`)
2. Criar Tarefa Básica → Nome: "Backup Estoque"
3. Disparador: Diário, 03:00
4. Ação: Iniciar um programa → `C:\Estoque\backup.bat`
5. Marque "Executar estando o usuário conectado ou não"

### 12.3 Agendar no Linux (cron)

```bash
crontab -e
0 3 * * * /opt/estoque/backup.sh
```

### 12.4 Restore

**SQLite:**
```bash
cp backups/estoque-2026-06-01_03-00-00.sqlite3 db.sqlite3
```

**PostgreSQL:**
```bash
psql -U estoque_user -d estoque < backups/estoque-2026-06-01_03-00-00-pg.sql
```

### 12.5 Política de retenção recomendada

- **Diário:** manter 7 dias
- **Semanal:** manter 4 semanas
- **Mensal:** manter 12 meses
- **Anual:** manter indefinidamente (cold storage)

---

## 13. Testes automatizados

### 13.1 Testes unitários Django (68 testes)

```bash
python manage.py test
```

Cobrem:
- `core`: Estoque coluna, cancelamento, sem N+1, renderização
- `stock`: FEFO, cancelamento, valor médio, ajustes, formulários
- `intelligence`: quantidade_recomendada, helpers da view
- `reports`: 19 testes de export
- `accounts`: preferências, login, redefinição de senha

### 13.2 Testes E2E Playwright (22 testes)

```bash
playwright install chromium      # primeira vez
python tests_e2e_fase5.py
```

Cobrem:
- Login, criação de categoria/fornecedor/produto
- Entrada e saída (verifica estoque na lista: 10 → 7)
- Dashboard, Inteligência, 4 downloads de relatórios
- Dark mode toggle + persistência após reload
- PWA: manifest, sw.js, ícones, /offline/
- Push endpoints: VAPID key, subscribe, unsubscribe, test_push

Screenshots de validação ficam em `tests_e2e_dark_light.png` e `tests_e2e_dark_dark.png`.

### 13.3 CI/CD (sugestão)

Crie `.github/workflows/tests.yml`:
```yaml
name: tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with: { python-version: '3.12' }
      - uses: actions/setup-node@v3
        with: { node-version: '18' }
      - run: pip install -r requirements.txt
      - run: npm install && npm run build:css
      - run: python manage.py test
      - run: playwright install chromium
      - run: python tests_e2e_fase5.py
        env:
          BASE: http://127.0.0.1:8000
```

---

## 14. Desenvolvimento (manutenção)

### 14.1 Criando uma migração

```bash
# Depois de alterar models.py
python manage.py makemigrations
python manage.py migrate

# Ver SQL gerado sem executar
python manage.py sqlmigrate stock 0002
```

### 14.2 Adicionando um novo app

1. `python manage.py startapp novo_app`
2. Adicione `"novo_app"` em `INSTALLED_APPS` no `settings.py`
3. Crie `novo_app/urls.py` e inclua em `estoque/urls.py`
4. Adicione o path ao `content` do `tailwind.config.js`
5. Rode `python manage.py makemigrations novo_app && python manage.py migrate`

### 14.3 Adicionando uma nova view/rota

1. Adicione a view em `app/views.py`
2. Adicione a rota em `app/urls.py` com `name="..."`
3. Crie o template em `templates/app/...`
4. Adicione ao menu em `templates/base.html` se for item permanente
5. **Recompile o CSS:** `npm run build:css`

### 14.4 Adicionando um novo relatório

1. Crie uma view em `reports/views.py` que retorna `HttpResponse` com content-type correto
2. Adicione a rota em `reports/urls.py`
3. Adicione o botão em `templates/dashboard.html` no painel "Relatórios"

### 14.5 Adicionando uma nova estatística ao dashboard

Edite `core/views.py::dashboard` e o template `templates/dashboard.html`. O Chart.js recebe `chart_labels`, `chart_data`, `chart_cores` via `json_script`.

### 14.6 Padrões de código

- **Service layer:** regras de negócio em `app/services.py`. Views e forms não fazem queries complexas.
- **Signals + time-stamp:** herde de `core.models.TimeStampedModel` para `created_at/updated_at/created_by/updated_by`.
- **Auditoria:** novos models em `core/stock/accounts` são auditados automaticamente. Para outros apps, importe os signals de `audit.signals`.
- **Templates:** use `dark:` em toda cor (`bg-white dark:bg-gray-800`, etc.). Use o componente `<div class="card card-body">` em vez de estilizar manualmente.
- **Forms:** herde de `BaseMovimentoForm` para entrada/saída/ajuste. Sempre faça `kwargs.pop("instance", None)` e `kwargs.pop("files", None)` no `__init__`.

### 14.7 Lint / format

Recomendado:
```bash
pip install ruff
ruff check .
ruff format .
```

---

## 15. Deploy em produção

### 15.1 Antes de subir (checklist)

- [ ] `DEBUG=False` no `.env`
- [ ] `SECRET_KEY` única (gerada com `secrets.token_urlsafe(50)`)
- [ ] `ALLOWED_HOSTS` com o domínio real
- [ ] `DATABASE_URL` apontando para PostgreSQL
- [ ] VAPID keys persistidas no `.env`
- [ ] HTTPS configurado (certificado válido)
- [ ] `collectstatic` rodado
- [ ] `migrate` rodado
- [ ] Backup configurado e testado
- [ ] Senha do `admin` alterada
- [ ] Firewall permitindo só 80/443

### 15.2 Linux + Gunicorn + Nginx

```bash
# 1. Servidor
sudo apt update
sudo apt install python3.11 python3-venv postgresql nginx

# 2. Banco
sudo -u postgres createuser estoque_user -P
sudo -u postgres createdb estoque -O estoque_user

# 3. Código
cd /opt
sudo git clone <repo> estoque
sudo chown -R www-data:www-data estoque
cd estoque
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py migrate

# 4. .env (não versionar)
cp .env.example .env
nano .env  # preencher variáveis

# 5. Gunicorn (systemd)
cat > /etc/systemd/system/estoque.service <<'EOF'
[Unit]
Description=Estoque Gunicorn
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/estoque
Environment="PATH=/opt/estoque/.venv/bin"
ExecStart=/opt/estoque/.venv/bin/gunicorn estoque.wsgi:application --bind 127.0.0.1:8000 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now estoque

# 6. Nginx
cat > /etc/nginx/sites-available/estoque <<'EOF'
server {
    listen 80;
    server_name estoque.exemplo.com;
    return 301 https://$server_name$request_uri;
}
server {
    listen 443 ssl http2;
    server_name estoque.exemplo.com;
    ssl_certificate /etc/letsencrypt/live/estoque.exemplo.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/estoque.exemplo.com/privkey.pem;
    client_max_body_size 20M;

    location /static/ {
        alias /opt/estoque/staticfiles/;
        expires 30d;
    }
    location /media/ {
        alias /opt/estoque/media/;
    }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/estoque /etc/nginx/sites-enabled/
sudo certbot --nginx -d estoque.exemplo.com
sudo systemctl restart nginx
```

### 15.3 Windows Server + Waitress + IIS

Para Windows como servidor de produção:

```cmd
pip install waitress
waitress-serve --listen=0.0.0.0:8000 estoque.wsgi:application
```

Configure o IIS como proxy reverso (ARR - Application Request Routing) ou use nginx para Windows.

### 15.4 Docker (alternativa)

Exemplo `Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["gunicorn", "estoque.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
```

---

## 16. Segurança e boas práticas

### Já implementado

- Senha mínima de 6 caracteres (Django validators)
- CSRF em todos os forms POST
- Auditoria automática de ações
- Senhas armazenadas com PBKDF2 + salt (padrão Django)
- Sessões com cookie HttpOnly
- WhiteNoise com hash nos assets (integridade)

### Você precisa fazer

- **Trocar a senha do `admin`** após o primeiro login
- **Gerar `SECRET_KEY` única** em produção
- **HTTPS obrigatório** (push notifications e cookies sensíveis)
- **Restringir ALLOWED_HOSTS** ao domínio real
- **Backup off-site** (S3, OneDrive, Google Drive)
- **Atualizar dependências** mensalmente: `pip list --outdated`
- **Logs de acesso:** monitore `/var/log/nginx/access.log`
- **Senhas fortes:** exija 12+ caracteres com maiúsculas, minúsculas, números e símbolos
- **Não exponha o `/admin/`** em redes públicas (use VPN ou restrição de IP)

### Boas práticas operacionais

- **Não delete movimentações** — use cancelamento
- **Não edite produtos** sem antes verificar o histórico
- **Crie um usuário para cada operador** (rastreabilidade)
- **Configure notificações push** para alertas críticos
- **Faça backup antes** de qualquer migração
- **Teste em dev** antes de subir para prod

---

## 17. Troubleshooting

### "CSRF verification failed"
- Você está acessando por um host não listado em `ALLOWED_HOSTS`. Adicione o domínio.
- Ou: cookie de sessão expirou. Faça logout/login.

### "no such column" ou "no such table"
- Banco de dados está desatualizado. Rode:
  ```bash
  python manage.py migrate
  ```

### "Class 'X' is not registered in namespace 'app'"
- Faltou `include("app.urls")` no `estoque/urls.py`.

### Tailwind: classes novas não aparecem
- Recompile o CSS: `npm run build:css`
- Verifique se o path do template está em `tailwind.config.js → content`

### PostgreSQL: "connection refused"
- PostgreSQL não está rodando (`sudo systemctl start postgresql`)
- Porta bloqueada no firewall
- Senha/usuário errados na `DATABASE_URL`

### Push notifications não chegam
- Verifique se VAPID keys estão no `.env` e persistidas
- Abra DevTools → Application → Service Workers → verifique se `/static/sw.js` está ativo
- Permissão do navegador foi negada
- HTTPS é obrigatório para push (exceto em localhost)

### "Port 8000 already in use"
- Outro processo está usando a porta. Mude: `python manage.py runserver 8001`
- Ou mate o processo: `netstat -ano | findstr :8000` → `taskkill /PID <pid>`

### Migration: "conflicting migrations"
- Você pulou uma migração. Rode: `python manage.py migrate --fake app_name 0001`
- Em último caso, apague o banco SQLite (perde dados) e rode `migrate` do zero

### Dark mode não persiste
- O navegador bloqueou `localStorage` (modo privado?)
- Verifique se não há cookie/script que limpa o storage

### E2E: "playwright._impl._errors.TimeoutError"
- Servidor não está rodando. Inicie: `start.bat` ou `python manage.py runserver`
- `playwright install chromium` não foi rodado
- Outro processo na porta 8765 (default do test)

---

## 18. Glossário

| Termo | Significado |
|-------|-------------|
| **FEFO** | First-Expire-First-Out. Lote que vence primeiro é consumido primeiro. |
| **PEPS** | Primeiro a Entrar, Primeiro a Sair (equivalente a FIFO em inglês). |
| **Estoque mínimo** | Quantidade que aciona alerta de "abaixo do mínimo". |
| **Estoque ideal** | Quantidade alvo após reposição. Sugestões de compra usam `ideal - atual`. |
| **Movimento** | Registro imutável de entrada ou saída. Nunca deletado, apenas cancelado. |
| **Lote** | Conjunto de um produto com mesma data de validade. Suporta múltiplos lotes por produto. |
| **Ruptura** | Momento em que o estoque zera. "Ruptura iminente" = vai zerar em ≤7 dias. |
| **Cobertura** | Quantos dias o estoque atual deve durar, dado o consumo médio. |
| **VAPID** | Voluntary Application Server Identification. Autentica o servidor que envia push. |
| **Service Worker** | Script JS que roda em background no navegador. Habilita offline e push. |
| **PWA** | Progressive Web App. Site que se comporta como app instalável. |
| **CSRF** | Cross-Site Request Forgery. Django protege com token. |
| **CSRF token** | Token aleatório validado em todos os POSTs. |
| **FEFO automático** | Sistema escolhe o lote (vencendo primeiro) sem o usuário selecionar. |
| **Valor médio** | Média ponderada das entradas recentes com valor unitário. |
| **PWA manifest** | Arquivo JSON que diz ao navegador como "instalar" o site como app. |
| **Maskable icon** | Ícone com área segura (sem cantos cortados) para adaptive icons Android. |
| **Auditoria** | Log imutável de "quem fez o quê, quando e de onde". |
| **Sentry / LogRocket** | Ferramentas externas de monitoring (não integradas, mas suportadas via `LOGGING`). |

---

## Anexo A — Comandos rápidos de referência

```bash
# Ambiente
python -m venv .venv
.venv\Scripts\activate                # Windows
source .venv/bin/activate             # Linux/Mac

# Dependências
pip install -r requirements.txt
npm install
npm run build:css

# Banco
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py changepassword admin
python manage.py shell                 # shell Django (acesso aos models)
python manage.py dbshell               # shell SQL
python manage.py dumpdata > dump.json  # exportar
python manage.py loaddata dump.json    # importar

# Servidor
python manage.py runserver             # dev
python manage.py runserver 0.0.0.0:8000  # dev, acesso na rede
gunicorn estoque.wsgi:application      # prod Linux

# Estáticos
python manage.py collectstatic --noinput

# Testes
python manage.py test                  # 68 unit tests
python tests_e2e_fase5.py             # 22 E2E tests

# Backup
backup.bat                             # auto-detecta SQLite/PostgreSQL

# Manutenção
python manage.py clearsessions         # limpa sessões expiradas
```

## Anexo B — Modelos de dados (referência rápida)

```python
# core/models.py
class Categoria:  nome (unique), descricao, ativa, cor
class Fornecedor: nome, cnpj, contato, telefone, email, lead_time_days, ativo
class Produto:    nome, codigo_interno (unique), categoria, fornecedor_principal,
                  unidade_medida, controla_validade, estoque_minimo, estoque_ideal,
                  localizacao, ativo
                  # property: quantidade_atual (soma de movimentos não cancelados)

# stock/models.py
class Lote:       produto, numero_lote, data_validade, data_entrada,
                  quantidade_inicial, quantidade_atual, nota_fiscal, ativo
                  # property: dias_para_vencer, vencido
class Movimento:  # IMUTÁVEL
                  produto, lote, tipo (ENTRADA/SAIDA), motivo, quantidade,
                  valor_unitario, valor_total, fornecedor, nota_fiscal,
                  responsavel, data_movimento, observacoes,
                  cancelado, motivo_cancelamento
class Alerta:     tipo, nivel, produto, lote, titulo, mensagem, lido, resolvido, dados

# accounts/models.py
class UserProfile: user (OneToOne), periodo_padrao (7/15/30/90/180/365),
                   dark_mode, push_enabled

# audit/models.py
class LogAuditoria:  url, metodo, usuario, acao, objeto_repr, dados, created_at

# notifications/models.py
class WebPushSubscription:  user, endpoint (unique), p256dh, auth, user_agent, ativo
```

---

**Versão do manual:** 1.0 (Fase 5 completa)
**Última atualização:** Junho 2026
**Mantido por:** Equipe de TI da Cozinha Industrial
