@echo off
chcp 65001 >nul
setlocal

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual nao encontrado. Execute setup.bat primeiro.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

if not exist "backups" mkdir backups

for /f "tokens=1-3 delims=/" %%a in ("%date%") do set DATA=%%c-%%b-%%a
for /f "tokens=1-2 delims=:" %%a in ("%time: =0%") do set HORA=%%a-%%b

:: Detecta o banco pelo .env
set DBTYPE=sqlite
findstr /C:"postgres://" .env >nul 2>nul
if not errorlevel 1 set DBTYPE=postgres
findstr /C:"postgresql://" .env >nul 2>nul
if not errorlevel 1 set DBTYPE=postgres

if "%DBTYPE%"=="postgres" (
    :: Extrai nome do banco do DATABASE_URL (pega o último segmento)
    for /f "tokens=*" %%b in ('findstr /C:"DATABASE_URL=" .env') do set DBURL=%%b
    for /f "tokens=2 delims=/" %%b in ("%DBURL%") do set DBNAME=%%b
    for /f "delims=" %%b in ("%DBNAME%") do set DBNAME=%%b
    set DBNAME=%DBNAME: =%
    :: Pega só o nome do banco (antes de ? se houver params)
    for /f "tokens=1 delims=?" %%b in ("%DBNAME%") do set DBNAME=%%b
    set ARQUIVO=backups\estoque-%DATA%_%HORA%-pg.sql
    echo Criando backup PostgreSQL: %ARQUIVO%
    where pg_dump >nul 2>nul
    if errorlevel 1 (
        echo [ERRO] pg_dump nao encontrado no PATH. Instale o PostgreSQL client.
        pause
        exit /b 1
    )
    pg_dump --no-owner --clean --if-exists %DBNAME% > "%ARQUIVO%"
    if errorlevel 1 (
        echo [ERRO] Falha em pg_dump.
        pause
        exit /b 1
    )
) else (
    set ARQUIVO=backups\estoque-%DATA%_%HORA%.sqlite3
    echo Criando backup SQLite: %ARQUIVO%
    copy /Y db.sqlite3 "%ARQUIVO%" >nul
    if errorlevel 1 (
        echo [ERRO] Falha no backup.
        pause
        exit /b 1
    )
)

if exist "%ARQUIVO%" (
    echo [OK] Backup concluido.
    echo      Arquivo: %ARQUIVO%
) else (
    echo [ERRO] Falha no backup.
    pause
    exit /b 1
)
