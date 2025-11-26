@echo off
:: =================================
:: SCRIPT DE INICIALIZAÇÃO (VERSÃO 2 - Mais Robusta)
:: =================================
title Crash Bot ML
color 0A

:: 1. Define o caminho para a pasta RAIZ do projeto
:: Use aspas para garantir que "Meu Drive" funcione
set "PROJECT_PATH=C:\IA\Crash\ML"

:: 2. Define o caminho exato para o executável Python DENTRO do .venv
set "PYTHON_EXE=%PROJECT_PATH%\.venv\Scripts\python.exe"

:: 3. Define o caminho exato para o script do bot
set "BOT_SCRIPT=%PROJECT_PATH%\src\bot_controller.py"

:: 4. Muda para o diretório do projeto (necessário para o bot encontrar o config.json)
cd /d "%PROJECT_PATH%"
echo [INFO] Acessando diretorio: %PROJECT_PATH%

:: 5. Verifica se o Python do .venv existe
if not exist "%PYTHON_EXE%" (
    echo [ERRO] Nao foi encontrado o executavel Python no .venv!
    echo [ERRO] Caminho verificado: %PYTHON_EXE%
    echo Pressione qualquer tecla para sair...
    pause
    exit
)

:: 6. Executa o script do bot usando o Python do .venv DIRETAMENTE
echo [INFO] Iniciando o bot com o Python do .venv...
"%PYTHON_EXE%" "%BOT_SCRIPT%"

:: 7. Manter a janela aberta no final
echo [INFO] O bot foi encerrado.
pause
