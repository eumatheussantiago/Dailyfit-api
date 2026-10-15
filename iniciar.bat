@echo off
chcp 65001 >nul
title DailyFit
cd /d "%~dp0"

echo.
echo  ==============================
echo   DailyFit - iniciando o app
echo  ==============================
echo.

rem --- Procura o Python instalado ---
set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY (
    python --version >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo  [ERRO] O Python nao foi encontrado neste computador.
    echo.
    echo  1. Baixe em https://www.python.org/downloads/
    echo  2. Na instalacao, MARQUE a opcao "Add python.exe to PATH"
    echo  3. Depois de instalar, de dois cliques neste arquivo de novo.
    echo.
    start "" https://www.python.org/downloads/
    pause
    exit /b 1
)

rem --- Cria o ambiente do projeto (so na primeira vez) ---
if not exist ".venv\Scripts\python.exe" (
    echo  Preparando o ambiente pela primeira vez...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo  [ERRO] Nao foi possivel criar o ambiente virtual.
        pause
        exit /b 1
    )
)

rem --- Instala as dependencias ---
echo  Instalando dependencias (pode levar 1 minuto na primeira vez)...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
    echo  [ERRO] Falha ao instalar as dependencias. Verifique sua internet.
    pause
    exit /b 1
)

rem --- Abre o navegador alguns segundos depois do servidor ligar ---
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8000"

echo.
echo  App rodando em: http://127.0.0.1:8000
echo  Para DESLIGAR, feche esta janela ou aperte Ctrl + C.
echo.
".venv\Scripts\python.exe" -m uvicorn main:app --port 8000

echo.
echo  O servidor parou. Se apareceu algum erro acima, copie e mande para o Claude.
pause
