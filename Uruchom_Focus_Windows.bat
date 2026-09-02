@echo off
title Focus - AI Scenepack Generator Launcher
cd /d "%~dp0"
echo ===================================================
echo   Focus AI Scenepack Generator - Windows Launcher
echo ===================================================
echo.

:: 1. Check for Python
set PYTHON_CMD=
for %%P in (python.exe py.exe python3.exe) do (
    %%P --version >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_CMD=%%P
        goto :python_found
    )
)

echo [BŁĄD] Nie znaleziono zainstalowanego Pythona (3.10+) w Twoim systemie!
echo Pobierz i zainstaluj Python z oficjalnej strony: https://www.python.org/downloads/
echo UWAGA: Podczas instalacji ZAZNACZ pole "Add Python to PATH"!
echo.
pause
exit /b 1

:python_found
echo [OK] Wykryto Python: %PYTHON_CMD%
%PYTHON_CMD% --version

:: 2. Check and Create Virtual Environment
if not exist "venv\Scripts\python.exe" (
    echo [INFO] Tworzenie wirtualnego środowiska Pythona (venv)...
    %PYTHON_CMD% -m venv venv
    if errorlevel 1 (
        echo [BŁĄD] Nie udało się utworzyć środowiska wirtualnego!
        pause
        exit /b 1
    )
)

:: 3. Activate venv
call venv\Scripts\activate.bat

:: 4. Install / Update Requirements
echo [INFO] Sprawdzanie i instalowanie bibliotek (PySide6, OpenCV, Face Recognition)...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 (
    echo [BŁĄD] Wystąpił problem podczas instalacji bibliotek! Sprawdź połączenie z internetem.
    pause
    exit /b 1
)
echo [OK] Wszystkie biblioteki są zainstalowane i gotowe.

:: 5. Check for FFmpeg
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo [OSTRZEŻENIE] Nie wykryto komendy 'ffmpeg' w systemie!
    echo Próba automatycznej instalacji FFmpeg za pomocą winget...
    winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements >nul 2>&1
    where ffmpeg >nul 2>&1
    if errorlevel 1 (
        echo.
        echo [UWAGA] Aby wycinanie i renderowanie wideo działało, FFmpeg musi być zainstalowany!
        echo Pobierz FFmpeg z https://www.gyan.dev/ffmpeg/builds/ i dodaj do zmiennych PATH,
        echo lub otwórz terminal jako Administrator i wpisz: winget install ffmpeg
        echo.
    ) else (
        echo [OK] FFmpeg został pomyślnie zainstalowany!
    )
) else (
    echo [OK] Wykryto FFmpeg w systemie.
)

:: 6. Launch Application
echo.
echo [INFO] Uruchamianie nowoczesnego interfejsu Focus (Qt 6 / PySide6)...
"%~dp0venv\Scripts\python.exe" "%~dp0scenepack_generator_gui_qt.py"
if errorlevel 1 (
    echo.
    echo [BŁĄD] Aplikacja zakończyła działanie z błędem!
    echo Przeczytaj komunikat powyżej przed zamknięciem okna.
    pause
    exit /b 1
)

:: Normal exit without immediate close if user wants to see logs
echo [INFO] Dziękujemy za korzystanie z Focus!
timeout /t 3 >nul
exit /b 0
