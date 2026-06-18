@echo off
chcp 65001 >nul
echo Estoque Cozinha - Iniciando servidor de desenvolvimento...
echo URLs:
echo   App:   http://127.0.0.1:8000
echo   Admin: http://127.0.0.1:8000/admin
echo.
if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual nao encontrado. Execute setup.bat primeiro.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
python manage.py runserver 0.0.0.0:8000
pause
