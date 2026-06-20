@echo off
REM ============================================================
REM Autostart für Penumbra Mod Watcher
REM Wird von der Windows Task Scheduler bei Benutzeranmeldung
REM ausgeführt. Startet watchdog auf D:\Telegram Desktop.
REM ============================================================
cd /d "C:\coding\penumbra-batch-installer"
set LOGFILE="%TEMP%\penumbra-watcher-startup.log"

echo [%DATE% %TIME%] Starting Penumbra Watcher >> %LOGFILE%

"C:\Users\herme\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" watch_telegram.py >> %LOGFILE% 2>&1

echo [%DATE% %TIME%] Watcher exited with code %ERRORLEVEL% >> %LOGFILE%
