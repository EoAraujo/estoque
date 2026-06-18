@echo off
chcp 65001 >nul
echo Compilando Tailwind CSS (modo minificado)...
where npx >nul 2>nul
if errorlevel 1 (
    echo [ERRO] npx nao encontrado. Instale Node.js 18+ de https://nodejs.org
    pause
    exit /b 1
)
call npx tailwindcss -i .\static\src\input.css -o .\static\css\app.css --minify
if errorlevel 1 (
    echo [ERRO] Falha ao compilar CSS.
    pause
    exit /b 1
)
echo [OK] CSS compilado em static\css\app.css
