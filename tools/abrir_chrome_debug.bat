@echo off
echo Fechando Chrome existente...
taskkill /F /IM chrome.exe 2>nul
timeout /t 2 /nobreak >nul

echo Abrindo Chrome com remote debugging na porta 9222...

:: Tenta caminhos comuns do Chrome
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=C:\temp\chrome-debug
    goto :ok
)
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=C:\temp\chrome-debug
    goto :ok
)
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    start "" "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=C:\temp\chrome-debug
    goto :ok
)

echo Chrome nao encontrado! Abra manualmente com --remote-debugging-port=9222
pause
exit /b 1

:ok
echo Chrome aberto com sucesso!
echo Agora abra o jogo no Chrome e rode: python tools/ws_sniffer.py
timeout /t 3 /nobreak >nul
