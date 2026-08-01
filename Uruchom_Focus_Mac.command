#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Automatically remove macOS Gatekeeper quarantine flags
xattr -cr "$DIR" 2>/dev/null || true
xattr -dr com.apple.quarantine "$DIR" 2>/dev/null || true

echo "==================================================="
echo "   Focus AI Scenepack Generator - macOS Launcher"
echo "==================================================="
echo ""

# 1. Check for Python 3
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "[BŁĄD] Nie znaleziono zainstalowanego Pythona 3 w Twoim systemie!"
    echo "Pobierz i zainstaluj Python z: https://www.python.org/downloads/ lub użyj Homebrew: brew install python"
    echo ""
    read -p "Naciśnij dowolny klawisz, aby zamknąć..." -n1 -s
    echo ""
    exit 1
fi

echo "[OK] Wykryto Python: $PYTHON_CMD ($($PYTHON_CMD --version))"

# 2. Check and Create Virtual Environment
if [ ! -f "venv/bin/python" ]; then
    echo "[INFO] Tworzenie wirtualnego środowiska Pythona (venv)..."
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo "[BŁĄD] Nie udało się utworzyć środowiska wirtualnego!"
        read -p "Naciśnij dowolny klawisz, aby zamknąć..." -n1 -s
        exit 1
    fi
fi

# 3. Activate venv
source venv/bin/activate

# 4. Install / Update Requirements
echo "[INFO] Sprawdzanie i instalowanie bibliotek (PySide6, OpenCV, Face Recognition)..."
pip install --upgrade pip >/dev/null 2>&1
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[BŁĄD] Wystąpił problem podczas instalacji bibliotek! Sprawdź połączenie z internetem."
    read -p "Naciśnij dowolny klawisz, aby zamknąć..." -n1 -s
    exit 1
fi
echo "[OK] Wszystkie biblioteki są zainstalowane i gotowe."

# 5. Check for FFmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "[OSTRZEŻENIE] Nie wykryto komendy 'ffmpeg' w systemie!"
    if command -v brew &>/dev/null; then
        echo "Próba automatycznej instalacji FFmpeg przez Homebrew..."
        brew install ffmpeg
    else
        echo "[UWAGA] Aby wycinanie i renderowanie wideo działało, FFmpeg musi być zainstalowany!"
        echo "Zainstaluj Homebrew (https://brew.sh) i wpisz w terminalu: brew install ffmpeg"
        echo ""
    fi
else
    echo "[OK] Wykryto FFmpeg w systemie."
fi

# 6. Launch Application
echo ""
echo "[INFO] Uruchamianie nowoczesnego interfejsu Focus (Qt 6 / PySide6)..."
python scenepack_generator_gui_qt.py
if [ $? -ne 0 ]; then
    echo ""
    echo "[BŁĄD] Aplikacja zakończyła działanie z błędem!"
    echo "Przeczytaj komunikat powyżej przed zamknięciem okna."
    read -p "Naciśnij dowolny klawisz, aby zamknąć..." -n1 -s
    exit 1
fi

echo "[INFO] Dziękujemy za korzystanie z Focus!"
sleep 2
exit 0
