@echo off
REM =====================================================
REM  Setup Task Scheduler - NVIDIA NIM Scraper
REM  Esegui come Amministratore!
REM =====================================================

set TASK_NAME=NVIDIA_NIM_Free_Models_Scraper
set SCRIPT_PATH=C:\Users\matti\Desktop\free-models\nvidia_nim_scraper.py
set LOG_PATH=C:\Users\matti\Desktop\free-models\scraper.log

REM Trova Python automaticamente
for /f "delims=" %%i in ('where python') do set PYTHON_PATH=%%i

echo Python trovato: %PYTHON_PATH%
echo.

REM Crea la cartella se non esiste
if not exist "C:\Users\matti\Desktop\free-models" (
    mkdir "C:\Users\matti\Desktop\free-models"
    echo Cartella creata: C:\Users\matti\Desktop\free-models
)

REM Copia lo script nella cartella di destinazione
copy "%~dp0nvidia_nim_scraper.py" "C:\Users\matti\Desktop\free-models\nvidia_nim_scraper.py" /Y

REM Crea il Task Scheduler (ogni giorno alle 08:30)
schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\" >> \"%LOG_PATH%\" 2>&1" ^
  /sc daily ^
  /st 08:30 ^
  /ru "%USERNAME%" ^
  /f

if %ERRORLEVEL% == 0 (
    echo.
    echo ✅ Task schedulato con successo!
    echo    Nome:  %TASK_NAME%
    echo    Ora:   Ogni giorno alle 08:30
    echo    Log:   %LOG_PATH%
    echo.
    echo Per verificare: Apri "Utilità di pianificazione" ^> Libreria
    echo Per eseguire subito: schtasks /run /tn "%TASK_NAME%"
) else (
    echo.
    echo ❌ Errore nella creazione del task.
    echo    Assicurati di eseguire come Amministratore.
)

pause
