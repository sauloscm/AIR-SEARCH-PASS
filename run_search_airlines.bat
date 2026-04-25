@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
echo Iniciando o Motor de Busca Comparativo (Google x Azul x LATAM)...
echo Por favor, mantenha esta janela aberta. O processo demorara consideravelmente mais que o normal.
cd /d "%~dp0"

python src/main_airlines.py
