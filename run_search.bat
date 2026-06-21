@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
echo Iniciando o Motor de Busca de Passagens Aereas...
echo Por favor, mantenha esta janela aberta. O processo levara cerca de 30 minutos.
cd /d "%~dp0"

REM Verifica se as dependencias estao instaladas, caso contrario as instala
pip show playwright >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando dependencias na primeira execucao...
    pip install -r requirements.txt
    python -m playwright install chromium
)

python src/main.py
pause
