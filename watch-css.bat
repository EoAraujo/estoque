@echo off
chcp 65001 >nul
echo Monitorando alteracoes no Tailwind CSS (Ctrl+C para parar)...
call npx tailwindcss -i .\static\src\input.css -o .\static\css\app.css --watch
