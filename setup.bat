@echo off
chcp 65001 >nul
setlocal

echo ===============================================
echo   ESTOQUE COZINHA - Setup inicial (Windows)
echo ===============================================
echo.
echo Suporta SQLite (padrao) e PostgreSQL.
echo Para usar PostgreSQL, edite o .env apos este setup
echo e defina DATABASE_URL=postgres://usuario:senha@host:5432/banco
echo.

:: Verifica se Python esta instalado
where python >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Python nao encontrado.
    echo Instale Python 3.11+ de https://www.python.org/downloads/
    echo Lembre de marcar "Add Python to PATH" na instalacao.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER% detectado.
echo.

:: Cria venv se nao existir
if not exist ".venv" (
    echo [1/8] Criando ambiente virtual...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar venv.
        pause
        exit /b 1
    )
) else (
    echo [OK] Ambiente virtual ja existe.
)

:: Ativa venv
call .venv\Scripts\activate.bat
echo.

:: Instala dependencias Python
echo [2/8] Instalando dependencias Python...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias Python.
    pause
    exit /b 1
)
echo.

:: Instala dependencias Node (Tailwind)
where node >nul 2>nul
if errorlevel 1 (
    echo [AVISO] Node.js nao encontrado. Instale Node 18+ de https://nodejs.org
    echo         para poder recompilar o CSS do Tailwind.
) else (
    echo [3/8] Instalando dependencias Node (Tailwind)...
    call npm install
    if errorlevel 1 (
        echo [AVISO] Falha ao instalar dependencias Node. Pule para o proximo passo.
    ) else (
        echo [4/8] Compilando CSS do Tailwind...
        call npx tailwindcss -i .\static\src\input.css -o .\static\css\app.css --minify
    )
)
echo.

:: Copia .env
if not exist ".env" (
    echo [5/8] Criando arquivo .env...
    copy .env.example .env >nul
) else (
    echo [OK] .env ja existe.
)
echo.

:: Detecta banco
findstr /C:"postgres://" .env >nul 2>nul
if not errorlevel 1 (
    set DBTYPE=postgres
    echo [6/8] Detectado: PostgreSQL (verifique se o banco existe e esta acessivel)
) else (
    set DBTYPE=sqlite
    echo [6/8] Detectado: SQLite (padrao)
)
echo.

:: Aplica migracoes
echo [7/8] Aplicando migracoes...
python manage.py makemigrations core accounts stock intelligence audit notifications
python manage.py migrate
if errorlevel 1 (
    echo [ERRO] Falha nas migracoes.
    if "%DBTYPE%"=="postgres" (
        echo Verifique se o PostgreSQL esta rodando e se a DATABASE_URL no .env esta correta.
    )
    pause
    exit /b 1
)
echo.

:: Cria superusuario
echo [8/8] Verificando superusuario admin...
python manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); u=U.objects.filter(username='admin').first(); print('admin:EXISTE' if u else 'admin:CRIAR')" 2>nul > tmp_admin_check.txt
set /p HASADMIN= < tmp_admin_check.txt
del tmp_admin_check.txt
echo %HASADMIN% | findstr /C:"CRIAR" >nul
if not errorlevel 1 (
    echo Criando superusuario admin / admin123...
    python manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); u=U.objects.create_user(username='admin', password='admin123', email='admin@local', first_name='Admin', last_name='Sistema', is_staff=True, is_superuser=True, is_active=True); print('admin criado com sucesso.')"
) else (
    echo [OK] Superusuario admin ja existe.
)
echo.

echo ===============================================
echo   Instalacao concluida!
echo.
echo   Para iniciar o servidor:  start.bat
echo   Para fazer backup:         backup.bat
echo   Para recompilar o CSS:    build-css.bat
echo.
echo   URLs:
echo     App:   http://127.0.0.1:8000
echo     Admin: http://127.0.0.1:8000/admin
echo.
echo   Login padrao: admin / admin123
echo ===============================================
echo.

set /p STARTNOW=Deseja iniciar o servidor agora? (S/N):
if /I "%STARTNOW%"=="S" (
    call start.bat
) else (
    echo Execute start.bat quando quiser iniciar.
    pause
)
