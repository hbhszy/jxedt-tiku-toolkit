@echo off
chcp 65001 >nul
set "APP_URL=file:///%~dp0index.html"
set "APP_URL=%APP_URL:\=/%"
set "APP_URL=%APP_URL: =%%20%"

if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
    start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --app="%APP_URL%"
    exit /b 0
)
if exist "C:\Program Files\Microsoft\Edge\Application\msedge.exe" (
    start "" "C:\Program Files\Microsoft\Edge\Application\msedge.exe" --app="%APP_URL%"
    exit /b 0
)
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app="%APP_URL%"
    exit /b 0
)
start "" "%~dp0index.html"
