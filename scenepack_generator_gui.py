import sys
import os
import cv2
import face_recognition
import subprocess
from pathlib import Path
import tempfile
import shutil
import logging
import threading
import queue
import time
import platform
import zipfile
import gzip
import multiprocessing
from typing import List, Tuple
import urllib.request
import tkinter as tk
import json
import numpy as np
import concurrent.futures
from PIL import Image, ImageDraw, ImageTk
import wave
import python_speech_features

# Global lock for thread-safe model downloads
CASCADE_DOWNLOAD_LOCK = threading.Lock()

# STRICT PERMANENT VERSIONING RULE: ALWAYS increment APP_VERSION by exactly +0.01 for EVERY user prompt/request.
APP_VERSION = "v0.95"

THEME_COLORS = {
    "red": "#C52233",
    "orange": "#E67E22",
    "yellow": "#F1C40F",
    "green": "#2ECC71",
    "blue": "#3498DB",
    "indigo": "#3F51B5",
    "violet": "#9B59B6",
    "pink": "#E91E63"
}

THEME_HOVER_COLORS = {
    "red": "#A31A29",
    "orange": "#C8691A",
    "yellow": "#D4AC0D",
    "green": "#25A25A",
    "blue": "#2874A6",
    "indigo": "#303F9F",
    "violet": "#7D3C98",
    "pink": "#C2185B"
}

TRANSLATIONS = {
    "English": {
        "dashboard": "Dashboard",
        "generator_tab": "Generator",
        "gallery_tab": "Beta / Character Gallery",
        "gallery_title": "Interactive Character Auto-Gallery (Beta)",
        "gallery_desc": "Pre-scan video to discover unique character faces. Click any card to select as target reference face!",
        "scan_chars": "Scan Video for Characters",
        "appearance": "Appearance Mode:",
        "theme": "Color Theme:",
        "language": "Language:",
        "play_sound": "Play sound on complete",
        "how_to_use": "How to Use",
        "changelog": "Changelog",
        "char_label": "Character",
        "detections_label": "detection(s)",
        "detections_badge": "{count} scene(s)",
        "preset_label": "Preset Profiles:",
        "preset_auto": "✨ Auto-Tune (Recommended)",
        "preset_fast": "⚡ Fast / Short Edits (TikTok/Reels)",
        "preset_cinematic": "🎬 Cinematic / Long Scenes",
        "preset_draft": "🚀 Ultra-Fast Scan (Draft)",
        "btn_auto_tune": "✨ Auto-Tune",
        "sel_video": "Select Input Video",
        "sel_ref": "Select Reference Face",
        "sel_output": "Select Save Location",
        "pad_before": "Padding Before (s):",
        "pad_after": "Padding After (s):",
        "max_gap": "Max Gap Tolerance (s):",
        "min_scene": "Min Scene Length (s):",
        "frame_skip": "Frame Skip Interval:",
        "vad_enable": "Smart Sentence Protection (VAD & Lip-Sync):",
        "vad_buffer": "Silence Snapping Buffer (ms):",
        "vad_speaker_enable": "Target Speaker Voice Matching:",
        "vad_speaker_threshold": "Voice Similarity Threshold:",
        "generate": "Generate",
        "review": "Review Results:",
        "play_orig": "Play Original Video",
        "play_result": "Play Result",
        "no_video": "No video selected",
        "no_image": "No image selected",
        "no_output": "No save location selected",
        "ready": "Ready to generate",
        "real_faces": "Real Faces",
        "anime": "Anime",
        "light": "Light",
        "dark": "Dark",
        "system": "System",
        "colors": ["red", "orange", "yellow", "green", "blue", "indigo", "violet", "pink"],
        "tt_pad_before": "Adds extra seconds before the detected face to prevent cutting off dialogue.",
        "tt_pad_after": "Adds extra seconds after a detected face, preventing dialogue cut-offs.",
        "tt_max_gap": "Bridges short gaps (like head turns or blinks), preventing premature scene cuts.",
        "tt_min_scene": "Ensures scenes are at least this long, filtering out micro-cuts.",
        "tt_frame_skip": "Higher = Faster processing, but might miss very brief shots.",
        "tt_vad_enable": "Uses Voice Activity Detection to extend clips to the nearest silence/pause, preventing mid-word or mid-sentence cut-offs.",
        "tt_vad_buffer": "The length of silence required to be considered a sentence/word break.",
        "tt_vad_speaker_enable": "Extracts the target character's voice from verified face frames and filters out background noise/narrators.",
        "tt_vad_speaker_threshold": "Cosine similarity threshold to verify speaker identity.",
        "tt_real_faces": "Uses deep learning facial landmarks. Best for real people or 3D characters.",
        "tt_anime": "Uses 2D cascade classifiers. Best for drawn/illustrated animation.",
        "tutorial_title": "How to Use Focus",
        "tutorial_close": "Got it!",
        "tutorial_body": (
            "• Supported Formats:\n"
            "  • Video: MP4, MKV, MOV, AVI, WEBM, FLV, M4V, TS, WMV\n"
            "  • Images: PNG, JPG, JPEG, WEBP, BMP, TIFF\n\n"
            "• Method 1 (Auto-Gallery Beta):\n"
            "  1. Open the 'Beta / Character Gallery' tab.\n"
            "  2. Click 'Scan Video for Characters' to auto-discover unique faces.\n"
            "  3. Click any character card to set it as your target reference face!\n\n"
            "• Method 2 (Manual Selection):\n"
            "  1. Select your input video file.\n"
            "  2. Choose a clear reference face image.\n"
            "  3. Choose the output directory for your scenepack.\n\n"
            "• Render Output Formats (16:9 vs 9:16):\n"
            "  • 16:9 Original: Extracts the clip exactly as it appears in the source video.\n"
            "  • 9:16 Vertical (Auto-Track): Auto-crops a vertical segment tracking the character's face.\n"
            "  • 9:16 Blurred Background: Places the 16:9 video over a blurred vertical background.\n\n"
            "• Settings & Filters:\n"
            "  • Real Faces vs Anime: Select 'Real Faces' for live-action or 'Anime' for 2D animation.\n"
            "  • Padding & Gap Tolerance: Add padding before/after clips and merge short blinks.\n"
            "  • Min. Scene Length: Prevents micro-cuts by enforcing a minimum duration (default 1.0s).\n\n"
            "• Generation: Click 'Generate Scenepack' and enjoy smooth, stutter-free clips!"
        ),
        "changelog_title": "Project History & Changelog",
        "changelog_close": "Close"
    },
    "Polski": {
        "dashboard": "Panel Główny",
        "generator_tab": "Generator",
        "gallery_tab": "Galeria Postaci (Beta)",
        "gallery_title": "Interaktywna Galeria Postaci (Beta)",
        "gallery_desc": "Przeskanuj wideo, aby automatycznie wykryć unikalne postacie. Kliknij kartę, aby wybrać cel!",
        "scan_chars": "Skanuj Wideo w Poszukiwaniu Postaci",
        "appearance": "Tryb Wyglądu:",
        "theme": "Motyw Kolorystyczny:",
        "language": "Język / Language:",
        "play_sound": "Odtwórz dźwięk po zakończeniu",
        "how_to_use": "Jak Używać",
        "changelog": "Lista Zmian",
        "char_label": "Postać",
        "detections_label": "wykryć",
        "detections_badge": "{count} ujęć",
        "preset_label": "Szybki Profil:",
        "preset_auto": "✨ Auto-Tune (Zalecane)",
        "preset_fast": "⚡ Szybkie Montaże (TikTok/Reels)",
        "preset_cinematic": "🎬 Kinowe / Długie Sceny",
        "preset_draft": "🚀 Bardzo Szybki Skan (Szkic)",
        "btn_auto_tune": "✨ Auto-Tune",
        "sel_video": "Wybierz Wideo Wejściowe",
        "sel_ref": "Wybierz Twarz Wzorcową",
        "sel_output": "Wybierz Miejsce Zapisu",
        "pad_before": "Margines Przed (s):",
        "pad_after": "Margines Po (s):",
        "max_gap": "Tolerancja Przerwy (s):",
        "min_scene": "Min. Długość Sceny (s):",
        "frame_skip": "Interwał Klatek:",
        "vad_enable": "Inteligentna Ochrona Zdań (VAD & Lip-Sync):",
        "vad_buffer": "Bufor Wyrównywania do Ciszy (ms):",
        "vad_speaker_enable": "Dopasowanie Głosu Celu:",
        "vad_speaker_threshold": "Próg Podobieństwa Głosu:",
        "generate": "Generuj Scenepack",
        "review": "Wynik:",
        "play_orig": "Odtwórz Oryginał",
        "play_result": "Odtwórz Wynik",
        "no_video": "Nie wybrano wideo",
        "no_image": "Nie wybrano zdjęcia",
        "no_output": "Nie wybrano miejsca zapisu",
        "ready": "Gotowy do generowania",
        "real_faces": "Prawdziwe Twarze",
        "anime": "Anime",
        "light": "Jasny",
        "dark": "Ciemny",
        "system": "Systemowy",
        "colors": ["czerwony", "pomarańczowy", "żółty", "zielony", "niebieski", "indigo", "fioletowy", "różowy"],
        "tt_pad_before": "Dodaje dodatkowe sekundy przed wykrytą twarzą, zapobiegając obcinaniu dialogów.",
        "tt_pad_after": "Dodaje dodatkowe sekundy po wykrytej twarzy, zapobiegając obcinaniu dialogów.",
        "tt_max_gap": "Łączy krótkie przerwy (np. odwrócenie głowy lub mrugnięcie), zapobiegając przedwczesnemu obcinaniu scen.",
        "tt_min_scene": "Gwarantuje, że sceny mają co najmniej podaną długość, eliminując miganie i micro-cięcia.",
        "tt_frame_skip": "Wyższa wartość = Szybsze przetwarzanie, ale może pominąć bardzo krótkie ujęcia.",
        "tt_vad_enable": "Używa algorytmu Voice Activity Detection, by przedłużyć ujęcie do najbliższej ciszy/pauzy, aby nie ucinać słów w połowie zdania.",
        "tt_vad_buffer": "Długość ciszy wymagana do uznania za koniec zdania/słowa.",
        "tt_vad_speaker_enable": "Wyodrębnia głos celu ze sprawdzonych klatek twarzy i filtruje tło/narratorów.",
        "tt_vad_speaker_threshold": "Próg podobieństwa cosinusowego do weryfikacji tożsamości mówcy.",
        "tt_real_faces": "Używa rozpoznawania twarzy głębokiego uczenia. Najlepsze dla ludzi i postaci 3D.",
        "tt_anime": "Używa klasyfikatorów 2D. Najlepsze dla rysowanej animacji 2D.",
        "tutorial_title": "Jak Używać Focus",
        "tutorial_close": "Zrozumiałem!",
        "tutorial_body": (
            "• Obsługiwane Formaty:\n"
            "  • Wideo: MP4, MKV, MOV, AVI, WEBM, FLV, M4V, TS, WMV\n"
            "  • Obrazy/Zdjęcia: PNG, JPG, JPEG, WEBP, BMP, TIFF\n\n"
            "• Sposób 1 (Auto-Galeria Beta):\n"
            "  1. Przejdź do zakładki 'Galeria Postaci (Beta)'.\n"
            "  2. Kliknij 'Skanuj Wideo w Poszukiwaniu Postaci', aby automatycznie wykryć twarze w tle.\n"
            "  3. Kliknij dowolną kartę postaci, aby ustawić jej twarz jako cel generowania!\n\n"
            "• Sposób 2 (Ręczny Wybór):\n"
            "  1. Wybierz plik wideo wejściowego.\n"
            "  2. Wybierz wyraźne zdjęcie twarzy wzorcowej.\n"
            "  3. Wybierz miejsce zapisu pliku scenepack.\n\n"
            "• Format Wyjściowy (16:9 vs 9:16):\n"
            "  • 16:9 Original: Zapisuje klip w oryginalnych proporcjach obrazu.\n"
            "  • 9:16 Vertical (Auto-Track): Dynamicznie kadruje wideo pionowo, śledząc twarz postaci.\n"
            "  • 9:16 Blurred Background: Umieszcza wideo 16:9 na rozmytym, pionowym tle (idealne na TikTok).\n\n"
            "• Ustawienia i Filtry:\n"
            "  • Prawdziwe Twarze vs Anime: Wybierz 'Prawdziwe Twarze' dla filmu lub 'Anime' dla animacji 2D.\n"
            "  • Marginesy i Tolerancja Przerw: Dodaj sekundy przed/po scenie oraz łącz krótkie mrugnięcia.\n"
            "  • Min. Długość Sceny: Zapobiega ucięciom i miganiu krótkich kadrów (domyślnie 1.0s).\n\n"
            "• Generowanie: Kliknij 'Generuj Scenepack' i ciesz się idealnie przyciętymi klipami!"
        ),
        "changelog_title": "Historia Projektu i Zmiany",
        "changelog_close": "Zamknij"
    },
    "Deutsch": {
        "dashboard": "Dashboard",
        "appearance": "Erscheinungsbild:",
        "theme": "Farbthema:",
        "language": "Sprache:",
        "play_sound": "Ton bei Fertigstellung abspielen",
        "how_to_use": "Anleitung",
        "changelog": "Änderungsprotokoll",
        "sel_video": "Eingabevideo auswählen",
        "sel_ref": "Referenzgesicht auswählen",
        "sel_output": "Speicherort auswählen",
        "pad_before": "Puffer vorher (s):",
        "pad_after": "Puffer nachher (s):",
        "max_gap": "Max. Lückenpuffer (s):",
        "frame_skip": "Frame-Intervall:",
        "generate": "Generieren",
        "review": "Ergebnisse überprüfen:",
        "play_orig": "Original abspielen",
        "play_result": "Ergebnis abspielen",
        "no_video": "Kein Video ausgewählt",
        "no_image": "Kein Bild ausgewählt",
        "no_output": "Kein Speicherort ausgewählt",
        "ready": "Bereit zum Generieren",
        "real_faces": "Echte Gesichter",
        "anime": "Anime",
        "light": "Hell",
        "dark": "Dunkel",
        "system": "System",
        "colors": ["rot", "orange", "gelb", "grün", "blau", "indigo", "violett", "rosa"],
        "tt_pad_before": "Fügt zusätzliche Sekunden vor dem erkannten Gesicht hinzu.",
        "tt_pad_after": "Fügt zusätzliche Sekunden nach dem erkannten Gesicht hinzu.",
        "tt_max_gap": "Überbrückt kurze Lücken (z.B. Kopfverdrehen oder Blinzeln), um vorzeitige Schnitte zu verhindern.",
        "tt_frame_skip": "Höher = Schneller, kann aber sehr kurze Auftritte verpassen.",
        "tt_real_faces": "Nutzt Deep Learning für echte Menschen oder 3D-Charaktere.",
        "tt_anime": "Nutzt 2D-Kaskadenklassifikatoren für 2D-Animationen.",
        "tutorial_title": "Focus Anleitung",
        "tutorial_close": "Verstanden!",
        "tutorial_body": (
            "• Schritt 1: Wählen Sie Ihre Videodatei aus.\n\n"
            "• Schritt 2: Wählen Sie ein deutliches Gesichtsbild des Charakters aus.\n\n"
            "• Schritt 3: Wählen Sie 'Echte Gesichter' oder 'Anime'.\n\n"
            "• Schritt 4: Passen Sie Puffer und Frame-Überspringen an.\n\n"
            "• Schritt 5: Klicken Sie auf Generieren!"
        ),
        "changelog_title": "Projekthistorie & Änderungsprotokoll",
        "changelog_close": "Schließen"
    },
    "Русский": {
        "dashboard": "Панель управления",
        "appearance": "Режим отображения:",
        "theme": "Цветовая тема:",
        "language": "Язык:",
        "play_sound": "Звук по завершении",
        "how_to_use": "Как использовать",
        "changelog": "История изменений",
        "sel_video": "Выбрать видео",
        "sel_ref": "Выбрать лицо",
        "sel_output": "Сохранить в...",
        "pad_before": "Отступ до (сек):",
        "pad_after": "Отступ после (сек):",
        "max_gap": "Макс. допуск паузы (сек):",
        "frame_skip": "Пропуск кадров:",
        "generate": "Создать сценпак",
        "review": "Результаты:",
        "play_orig": "Оригинал",
        "play_result": "Результат",
        "no_video": "Видео не выбрано",
        "no_image": "Изображение не выбрано",
        "no_output": "Место сохранения не выбрано",
        "ready": "Готово к работе",
        "real_faces": "Реальные лица",
        "anime": "Аниме",
        "light": "Светлая",
        "dark": "Тёмная",
        "system": "Системная",
        "colors": ["красный", "оранжевый", "жёлтый", "зелёный", "синий", "индиго", "фиолетовый", "розовый"],
        "tt_pad_before": "Добавляет секунды перед обнаруженным лицом, чтобы не обрезать диалог.",
        "tt_pad_after": "Добавляет секунды после обнаруженного лица.",
        "tt_max_gap": "Объединяет короткие паузы (поворот головы, моргание), предотвращая преждевременную обрезку.",
        "tt_frame_skip": "Выше = Быстрее, но может пропустить короткие кадры.",
        "tt_real_faces": "Использует глубокое обучение для реальных людей и 3D персонажей.",
        "tt_anime": "Использует 2D классификаторы для аниме.",
        "tutorial_title": "Инструкция Focus",
        "tutorial_close": "Понятно!",
        "tutorial_body": (
            "• Шаг 1: Выберите исходный видеофайл.\n\n"
            "• Шаг 2: Выберите четкое фото персонажа.\n\n"
            "• Шаг 3: Выберите 'Реальные лица' или 'Аниме'.\n\n"
            "• Шаг 4: Настройте отступы времени и пропуск кадров.\n\n"
            "• Шаг 5: Нажмите Создать и дождитесь результата!"
        ),
        "changelog_title": "История проекта и изменений",
        "changelog_close": "Закрыть"
    },
    "Українська": {
        "dashboard": "Панель керування",
        "appearance": "Режим вигляду:",
        "theme": "Колірна тема:",
        "language": "Мова:",
        "play_sound": "Звук після завершення",
        "how_to_use": "Як використовувати",
        "changelog": "Журнал змін",
        "sel_video": "Обрати відео",
        "sel_ref": "Обрати обличчя",
        "sel_output": "Зберегти в...",
        "pad_before": "Відступ до (сек):",
        "pad_after": "Відступ після (сек):",
        "max_gap": "Макс. допуск паузи (сек):",
        "frame_skip": "Пропуск кадрів:",
        "generate": "Створити сценпак",
        "review": "Результати:",
        "play_orig": "Оригінал",
        "play_result": "Результат",
        "no_video": "Відео не обрано",
        "no_image": "Зображення не обрано",
        "no_output": "Місце збереження не обрано",
        "ready": "Готово до роботи",
        "real_faces": "Реальні обличчя",
        "anime": "Аніме",
        "light": "Світлий",
        "dark": "Темний",
        "system": "Системний",
        "colors": ["червоний", "помаранчевий", "жовтий", "зелений", "синій", "індиго", "фіолетовий", "рожевий"],
        "tt_pad_before": "Додає секунди перед виявленим обличчям.",
        "tt_pad_after": "Додає секунди після виявленого обличчя.",
        "tt_max_gap": "Об'єднує короткі паузи (поворот голови, кліпання), запобігаючи передчасній обрізці.",
        "tt_frame_skip": "Більше = Швидше, але може пропустити короткі появи.",
        "tt_real_faces": "Використовує глибоке навчання для реальних людей або 3D.",
        "tt_anime": "Використовує 2D класифікатори для 2D анімації.",
        "tutorial_title": "Інструкція Focus",
        "tutorial_close": "Зрозуміло!",
        "tutorial_body": (
            "• Крок 1: Оберіть відеофайл.\n\n"
            "• Крок 2: Оберіть чітке фото персонажа.\n\n"
            "• Крок 3: Оберіть 'Реальні обличчя' або 'Аніме'.\n\n"
            "• Крок 4: Налаштуйте відступи часу та пропуск кадрів.\n\n"
            "• Крок 5: Натисніть Створити!"
        ),
        "changelog_title": "Історія проекту та змін",
        "changelog_close": "Закрити"
    },
    "Español": {
        "dashboard": "Panel de control",
        "appearance": "Modo de apariencia:",
        "theme": "Tema de color:",
        "language": "Idioma:",
        "play_sound": "Reproducir sonido al finalizar",
        "how_to_use": "Cómo usar",
        "changelog": "Historial de cambios",
        "sel_video": "Seleccionar video de entrada",
        "sel_ref": "Seleccionar rostro de referencia",
        "sel_output": "Ubicación de guardado",
        "pad_before": "Margen anterior (s):",
        "pad_after": "Margen posterior (s):",
        "max_gap": "Tolerancia de pausa (s):",
        "frame_skip": "Salto de fotogramas:",
        "generate": "Generar",
        "review": "Revisar resultados:",
        "play_orig": "Reproducir original",
        "play_result": "Reproducir resultado",
        "no_video": "Ningún video seleccionado",
        "no_image": "Ninguna imagen seleccionada",
        "no_output": "Ubicación no seleccionada",
        "ready": "Listo para generar",
        "real_faces": "Caras reales",
        "anime": "Anime",
        "light": "Claro",
        "dark": "Oscuro",
        "system": "Sistema",
        "colors": ["rojo", "naranja", "amarillo", "verde", "azul", "índigo", "violeta", "rosa"],
        "tt_pad_before": "Agrega segundos adicionales antes del rostro detectado.",
        "tt_pad_after": "Agrega segundos adicionales después del rostro detectado.",
        "tt_max_gap": "Une pequeñas pausas (parpadeos o giros de cabeza) para evitar cortes prematuros.",
        "tt_frame_skip": "Mayor = Más rápido, pero puede perder apariciones breves.",
        "tt_real_faces": "Usa aprendizaje profundo para personas reales o personajes 3D.",
        "tt_anime": "Usa clasificadores en cascada 2D para animación.",
        "tutorial_title": "Guía de Focus",
        "tutorial_close": "¡Entendido!",
        "tutorial_body": (
            "• Paso 1: Seleccione su archivo de video.\n\n"
            "• Paso 2: Seleccione una imagen clara del personaje.\n\n"
            "• Paso 3: Elija 'Caras reales' o 'Anime'.\n\n"
            "• Paso 4: Ajuste márgenes y salto de fotogramas.\n\n"
            "• Paso 5: ¡Haga clic en Generar!"
        ),
        "changelog_title": "Historial y Registro de Cambios",
        "changelog_close": "Cerrar"
    },
    "Français": {
        "dashboard": "Tableau de bord",
        "appearance": "Mode d'apparence:",
        "theme": "Thème de couleur:",
        "language": "Langue:",
        "play_sound": "Jouer un son à la fin",
        "how_to_use": "Guide d'utilisation",
        "changelog": "Journal des modifications",
        "sel_video": "Sélectionner la vidéo",
        "sel_ref": "Sélectionner le visage",
        "sel_output": "Emplacement de sauvegarde",
        "pad_before": "Marge avant (s):",
        "pad_after": "Marge arrière (s):",
        "max_gap": "Tolérance de pause (s):",
        "frame_skip": "Saut d'images:",
        "generate": "Générer",
        "review": "Résultats:",
        "play_orig": "Lire l'original",
        "play_result": "Lire le résultat",
        "no_video": "Aucune vidéo sélectionnée",
        "no_image": "Aucune image sélectionnée",
        "no_output": "Aucun emplacement sélectionné",
        "ready": "Prêt à générer",
        "real_faces": "Visages réels",
        "anime": "Anime",
        "light": "Clair",
        "dark": "Sombre",
        "system": "Système",
        "colors": ["rouge", "orange", "jaune", "vert", "bleu", "indigo", "violet", "rose"],
        "tt_pad_before": "Ajoute des secondes avant le visage détecté.",
        "tt_pad_after": "Ajoute des secondes après le visage détecté.",
        "tt_max_gap": "Fusionne les courtes pauses (clignements ou tours de tête) pour éviter les coupes prématurées.",
        "tt_frame_skip": "Plus élevé = Plus rapide, mais peut manquer des scènes très courtes.",
        "tt_real_faces": "Utilise l'apprentissage profond pour les personnes réelles ou 3D.",
        "tt_anime": "Utilise des classificateurs 2D pour l'animation.",
        "tutorial_title": "Guide Focus",
        "tutorial_close": "Compris !",
        "tutorial_body": (
            "• Étape 1 : Sélectionnez votre fichier vidéo.\n\n"
            "• Étape 2 : Sélectionnez une image claire du personnage.\n\n"
            "• Étape 3 : Choisissez 'Visages réels' ou 'Anime'.\n\n"
            "• Étape 4 : Ajustez les marges et le saut d'images.\n\n"
            "• Étape 5 : Cliquez sur Générer !"
        ),
        "changelog_title": "Historique du Projet & Modifications",
        "changelog_close": "Fermer"
    },
    "日本語": {
        "dashboard": "ダッシュボード",
        "appearance": "外観モード:",
        "theme": "カラーテーマ:",
        "language": "言語:",
        "play_sound": "完了時に音を鳴らす",
        "how_to_use": "使い方",
        "changelog": "更新履歴",
        "sel_video": "入力動画を選択",
        "sel_ref": "参照顔画像を選択",
        "sel_output": "保存先を選択",
        "pad_before": "前パディング(秒):",
        "pad_after": "後パディング(秒):",
        "max_gap": "最大許容間隔(秒):",
        "frame_skip": "フレームスキップ間隔:",
        "generate": "生成開始",
        "review": "結果の確認:",
        "play_orig": "元の動画を再生",
        "play_result": "結果を再生",
        "no_video": "動画が選択されていません",
        "no_image": "画像が選択されていません",
        "no_output": "保存先が選択されていません",
        "ready": "生成の準備ができました",
        "real_faces": "実写顔",
        "anime": "アニメ",
        "light": "ライト",
        "dark": "ダーク",
        "system": "システム",
        "colors": ["赤", "オレンジ", "黄色", "緑", "青", "インディゴ", "紫", "ピンク"],
        "tt_pad_before": "検出された顔の前に余分な秒数を追加します。",
        "tt_pad_after": "検出された顔の後ろに余分な秒数を追加します。",
        "tt_max_gap": "顔の横向きやまばたきによる短い途切れを自動連結し、カットを防止します。",
        "tt_frame_skip": "値が大きいほど高速になりますが、短い登場を見逃す可能性があります。",
        "tt_real_faces": "ディープラーニングを使用して実写人物や3Dキャラを検出します。",
        "tt_anime": "2Dカスケード分類器を使用して2Dアニメを検出します。",
        "tutorial_title": "Focus 使い方ガイド",
        "tutorial_close": "了解！",
        "tutorial_body": (
            "• ステップ 1: 動画ファイルを選択します。\n\n"
            "• ステップ 2: 抽出したいキャラの顔画像を選択します。\n\n"
            "• ステップ 3: '実写顔' または 'アニメ' を選択します。\n\n"
            "• ステップ 4: パディングとフレームスキップを調整します。\n\n"
            "• ステップ 5: 生成開始をクリックします！"
        ),
        "changelog_title": "プロジェクト履歴と更新ログ",
        "changelog_close": "閉じる"
    }
}

def get_translation(lang_name: str, key: str) -> str:
    """Safely retrieves a localized string with fallback to English and key name."""
    lang_dict = TRANSLATIONS.get(lang_name, TRANSLATIONS.get("English", {}))
    if key in lang_dict:
        return lang_dict[key]
    return TRANSLATIONS.get("English", {}).get(key, key)

def canonicalize_mode(mode_str: str) -> str:
    """Converts any localized mode string (e.g. 'Prawdziwe Twarze', 'Echte Gesichter') to 'Real Faces' or 'Anime'."""
    if not mode_str:
        return "Real Faces"
    for lang_dict in TRANSLATIONS.values():
        anime_val = lang_dict.get("anime")
        if anime_val and mode_str.strip().lower() in [anime_val.lower(), "anime", "аниме"]:
            return "Anime"
    return "Real Faces"

def make_square_crop(frame, top, right, bottom, left, pad_ratio=0.30):
    """Crops a clean 1:1 square face ROI from frame with neutral background padding if needed."""
    h, w = frame.shape[:2]
    fh = bottom - top
    fw = right - left
    center_y = top + fh // 2
    center_x = left + fw // 2
    side = int(max(fw, fh) * (1.0 + pad_ratio * 2))
    
    crop_top = max(0, center_y - side // 2)
    crop_bottom = min(h, center_y + side // 2)
    crop_left = max(0, center_x - side // 2)
    crop_right = min(w, center_x + side // 2)
    
    crop = frame[crop_top:crop_bottom, crop_left:crop_right]
    if crop.size == 0:
        return None
        
    ch, cw = crop.shape[:2]
    if ch != cw:
        max_dim = max(ch, cw)
        square = np.full((max_dim, max_dim, 3), 35, dtype=np.uint8)
        off_y = (max_dim - ch) // 2
        off_x = (max_dim - cw) // 2
        square[off_y:off_y+ch, off_x:off_x+cw] = crop
        crop = square
        
    return crop

def extract_anime_face_features(crop_bgr):
    """
    Extracts a 1D Hue histogram (masked to center face ROI, invariant to shadows/lighting shifts),
    2D HS histogram, and a 256-bit perceptual dHash feature vector from an anime face crop.
    """
    h, w = crop_bgr.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.ellipse(mask, (w // 2, h // 2), (max(1, int(w * 0.38)), max(1, int(h * 0.42))), 0, 0, 360, 255, -1)

    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    # 1D Hue Histogram (18 bins for 180 degrees Hue range, 10 deg per bin)
    hue_hist = cv2.calcHist([hsv], [0], mask, [18], [0, 180])
    cv2.normalize(hue_hist, hue_hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

    # 2D Hue-Sat Histogram (16x16 bins for full color profile)
    hs_hist = cv2.calcHist([hsv], [0, 1], mask, [16, 16], [0, 180, 0, 256])
    cv2.normalize(hs_hist, hs_hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    # 16x16 Perceptual dHash (256 bits)
    resized = cv2.resize(gray, (17, 16))
    dhash = (resized[:, 1:] > resized[:, :-1]).flatten()

    return hue_hist, hs_hist, dhash

def is_anime_feature_match(feat1, feat2) -> bool:
    hue_hist1, hs_hist1, dhash1 = feat1
    hue_hist2, hs_hist2, dhash2 = feat2

    hue_corr = float(cv2.compareHist(hue_hist1, hue_hist2, cv2.HISTCMP_CORREL))
    hs_corr = float(cv2.compareHist(hs_hist1, hs_hist2, cv2.HISTCMP_CORREL))
    dhash_dist = float(np.count_nonzero(dhash1 != dhash2)) / float(len(dhash1))

    # Match if Hue color correlation > 0.40 OR full HS correlation > 0.35 OR (Hue corr > 0.20 and dHash dist <= 0.36)
    if hue_corr > 0.40:
        return True
    if hs_corr > 0.35:
        return True
    if hue_corr > 0.20 and dhash_dist <= 0.36:
        return True
    return False

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def set_text(self, text):
        self.text = text

    def enter(self, event=None):
        if not self.text:
            return
            
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#2b2b2b", foreground="#ffffff", 
                         relief='solid', borderwidth=1,
                         font=("Helvetica", 12, "normal"), padx=8, pady=4)
        label.pack(ipadx=1)
        
        tw.update_idletasks()
        screen_width = tw.winfo_screenwidth()
        tt_width = tw.winfo_width()
        if x + tt_width > screen_width:
            x = screen_width - tt_width - 10
            
        tw.wm_geometry(f"+{x}+{y}")

    def leave(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

import customtkinter as ctk
from tkinter import filedialog, messagebox

# Custom Logging Handler to forward logs to our GUI Queue
class TextboxLogHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        msg = self.format(record)
        self.log_queue.put(("log", msg))

class ScenePackGenerator:
    """
    Backend service for generating video scenepacks.
    """
    def __init__(self, log_queue, frame_skip: int = 15, tolerance: float = 0.6, mode: str = "Real Faces"):
        self.log_queue = log_queue
        self.frame_skip = frame_skip
        self.tolerance = tolerance
        self.mode = mode
        
        # Determine the directory where the script is located
        if platform.system() == "Windows":
            self.app_dir = Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / "Focus"
        else:
            self.app_dir = Path(os.path.expanduser('~/Library/Application Support/Focus'))
        self.app_dir.mkdir(parents=True, exist_ok=True)
            
        self.anime_cascade_path = self.app_dir / "lbpcascade_animeface.xml"
        
        self.bin_dir = self.app_dir / "bin"
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        exe_suffix = ".exe" if platform.system() == "Windows" else ""
        self.ffmpeg_path = self.bin_dir / f"ffmpeg{exe_suffix}"
        self.ffprobe_path = self.bin_dir / f"ffprobe{exe_suffix}"

    def _check_and_download_ffmpeg(self):
        if self.ffmpeg_path.exists() and self.ffprobe_path.exists():
            return
            
        if shutil.which("ffmpeg") and shutil.which("ffprobe"):
            self.ffmpeg_path = Path(shutil.which("ffmpeg"))
            self.ffprobe_path = Path(shutil.which("ffprobe"))
            return
            
        if platform.system() not in ["Darwin", "Windows"]:
            self.log_queue.put(("log", "Warning: Auto-download for FFmpeg is currently only supported on macOS and Windows. Please install FFmpeg manually."))
            return

        if platform.system() == "Windows":
            if not self.ffmpeg_path.exists() or not self.ffprobe_path.exists():
                self.log_queue.put(("log", "Downloading FFmpeg for Windows (this may take a minute)..."))
                url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
                zip_path = self.bin_dir / "ffmpeg_win.zip"
                urllib.request.urlretrieve(url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    for file_info in zip_ref.infolist():
                        if file_info.filename.endswith('ffmpeg.exe'):
                            file_info.filename = 'ffmpeg.exe'
                            zip_ref.extract(file_info, self.bin_dir)
                        elif file_info.filename.endswith('ffprobe.exe'):
                            file_info.filename = 'ffprobe.exe'
                            zip_ref.extract(file_info, self.bin_dir)
                zip_path.unlink()
                self.log_queue.put(("log", "FFmpeg downloaded successfully."))
            return

        if not self.ffmpeg_path.exists():
            self.log_queue.put(("log", "Downloading static FFmpeg binary (this may take a minute)..."))
            if platform.machine() in ["arm64", "aarch64"]:
                url = "https://github.com/eugeneware/ffmpeg-static/releases/download/b6.1.1/ffmpeg-darwin-arm64.gz"
                gz_path = self.bin_dir / "ffmpeg.gz"
                urllib.request.urlretrieve(url, gz_path)
                with gzip.open(gz_path, 'rb') as f_in:
                    with open(self.ffmpeg_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                gz_path.unlink()
            else:
                url = "https://evermeet.cx/ffmpeg/getrelease/zip"
                zip_path = self.bin_dir / "ffmpeg.zip"
                urllib.request.urlretrieve(url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(self.bin_dir)
                zip_path.unlink()
            os.chmod(self.ffmpeg_path, 0o755)
            
        if not self.ffprobe_path.exists():
            self.log_queue.put(("log", "Downloading static FFprobe binary..."))
            if platform.machine() in ["arm64", "aarch64"]:
                url = "https://github.com/eugeneware/ffmpeg-static/releases/download/b6.1.1/ffprobe-darwin-arm64.gz"
                gz_path = self.bin_dir / "ffprobe.gz"
                urllib.request.urlretrieve(url, gz_path)
                with gzip.open(gz_path, 'rb') as f_in:
                    with open(self.ffprobe_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                gz_path.unlink()
            else:
                url = "https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip"
                zip_path = self.bin_dir / "ffprobe.zip"
                urllib.request.urlretrieve(url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(self.bin_dir)
                zip_path.unlink()
            os.chmod(self.ffprobe_path, 0o755)

    def _download_anime_cascade(self):
        with CASCADE_DOWNLOAD_LOCK:
            if not self.anime_cascade_path.exists() or self.anime_cascade_path.stat().st_size < 50000:
                self.log_queue.put(("log", "Downloading anime face cascade model..."))
                url = "https://raw.githubusercontent.com/nagadomi/lbpcascade_animeface/master/lbpcascade_animeface.xml"
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response, open(self.anime_cascade_path, 'wb') as out_file:
                        shutil.copyfileobj(response, out_file)
                        
                    if self.anime_cascade_path.stat().st_size < 50000:
                        if self.anime_cascade_path.exists():
                            self.anime_cascade_path.unlink()
                        raise RuntimeError("Downloaded file size is under 50KB; download was likely blocked or corrupted.")
                        
                    self.log_queue.put(("log", "Successfully downloaded anime face cascade model."))
                except Exception as e:
                    if self.anime_cascade_path.exists():
                        self.anime_cascade_path.unlink()
                    self.log_queue.put(("log", f"Failed to download anime cascade model: {e}"))
                    raise RuntimeError(f"Failed to download anime cascade model: {e}")

    def _get_best_video_codec_and_args(self) -> Tuple[str, List[str]]:
        """Probes FFmpeg for available hardware video encoders and returns the fastest supported codec and its optimal speed arguments."""
        if hasattr(self, "_cached_best_vcodec") and self._cached_best_vcodec is not None:
            return self._cached_best_vcodec

        if platform.system() == "Darwin":
            candidates = [
                ("h264_videotoolbox", []),
                ("libx264", ["-preset", "veryfast"])
            ]
        elif platform.system() == "Windows":
            candidates = [
                ("h264_nvenc", ["-preset", "fast"]),
                ("h264_qsv", ["-preset", "veryfast"]),
                ("h264_amf", ["-quality", "speed"]),
                ("h264_mf", []),
                ("libx264", ["-preset", "veryfast"])
            ]
        else:
            candidates = [
                ("h264_nvenc", ["-preset", "fast"]),
                ("h264_vaapi", []),
                ("h264_qsv", ["-preset", "veryfast"]),
                ("h264_amf", ["-quality", "speed"]),
                ("libx264", ["-preset", "veryfast"])
            ]
            
        for codec, args in candidates:
            if codec == "libx264":
                self._cached_best_vcodec = (codec, args)
                logging.info(f"Using CPU video encoder fallback: '{codec}'")
                return codec, args
            try:
                cmd = [
                    str(self.ffmpeg_path), "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "nullsrc=s=320x240:d=0.05",
                    "-c:v", codec
                ] + args + ["-f", "null", "-"]
                res = subprocess.run(cmd, capture_output=True, timeout=5)
                if res.returncode == 0:
                    self._cached_best_vcodec = (codec, args)
                    logging.info(f"Hardware acceleration enabled: selected GPU video encoder '{codec}'")
                    return codec, args
            except Exception as e:
                logging.debug(f"Codec probe failed for {codec}: {e}")
                
        self._cached_best_vcodec = ("libx264", ["-preset", "veryfast"])
        return self._cached_best_vcodec

    def load_reference_face(self, ref_image_path: Path):
        if not ref_image_path.is_file():
            raise FileNotFoundError(f"Reference image not found: {ref_image_path}")
            
        logging.info(f"Loading reference face from '{ref_image_path.name}'...")
        
        if self.mode == "Real Faces":
            image = face_recognition.load_image_file(str(ref_image_path))
            encodings = face_recognition.face_encodings(image)
            
            if not encodings:
                raise ValueError(f"No face found in reference image: {ref_image_path.name}")
                
            return encodings[0]
        else:
            # Anime Mode - Cascade classifiers detect ANY anime face, not a specific character.
            # We don't need reference encodings, so we just return None.
            return None

    def _get_video_duration(self, video_path: Path) -> float:
        cmd = [
            str(self.ffprobe_path), '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            val = float(result.stdout.strip())
            if val > 0:
                return val
        except ValueError:
            pass
            
        logging.warning("Could not determine exact video duration via ffprobe. Falling back to OpenCV.")
        cap = cv2.VideoCapture(str(video_path))
        try:
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                if fps > 0 and total_frames > 0:
                    return total_frames / fps
        finally:
            cap.release()
        return float('inf')

    def merge_intervals(self, timestamps: List[Tuple[float, float]], padding_before: float, padding_after: float, duration: float, max_gap_tolerance: float = 1.5, min_scene_duration: float = 1.0) -> List[Tuple[float, float, float]]:
        if not timestamps:
            return []
            
        sorted_ts = sorted([t for t in timestamps if t[0] >= 0.0], key=lambda x: x[0])
        if not sorted_ts:
            return []

        runs = []
        run_start = sorted_ts[0][0]
        run_end = sorted_ts[0][0]
        run_x_vals = [sorted_ts[0][1]]
        
        for t, x_val in sorted_ts[1:]:
            if t - run_end <= max_gap_tolerance:
                run_end = t
                run_x_vals.append(x_val)
            else:
                avg_x = sum(run_x_vals) / len(run_x_vals) if run_x_vals else 0.5
                runs.append((run_start, run_end, avg_x))
                run_start = t
                run_end = t
                run_x_vals = [x_val]
                
        avg_x = sum(run_x_vals) / len(run_x_vals) if run_x_vals else 0.5
        runs.append((run_start, run_end, avg_x))
        
        padded_intervals = []
        for start, end, avg_x in runs:
            clip_start = max(0.0, start - padding_before)
            clip_end = min(duration, end + padding_after) if duration > 0 and duration != float('inf') else (end + padding_after)
            if clip_end > clip_start + 0.05: # Filter out sub-50ms micro-intervals
                padded_intervals.append((clip_start, clip_end, avg_x))
            
        if not padded_intervals:
            return []

        merged = []
        curr_start, curr_end, curr_x = padded_intervals[0]
        curr_x_list = [curr_x]
        
        for start, end, avg_x in padded_intervals[1:]:
            if start <= curr_end:
                curr_end = max(curr_end, end)
                curr_x_list.append(avg_x)
            else:
                merged_x = sum(curr_x_list) / len(curr_x_list)
                merged.append((curr_start, curr_end, merged_x))
                curr_start, curr_end = start, end
                curr_x_list = [avg_x]
                
        merged_x = sum(curr_x_list) / len(curr_x_list)
        merged.append((curr_start, curr_end, merged_x))
        
        # Apply Minimum Scene Duration filter
        final_scenes = []
        for start, end, avg_x in merged:
            scene_dur = end - start
            if scene_dur < min_scene_duration:
                needed = min_scene_duration - scene_dur
                new_end = end + needed
                if duration > 0 and duration != float('inf'):
                    new_end = min(duration, new_end)
                final_scenes.append((start, new_end, avg_x))
            else:
                final_scenes.append((start, end, avg_x))

        if not final_scenes:
            return []

        # Secondary merge to combine any overlapping expanded scenes
        result = []
        c_start, c_end, c_x = final_scenes[0]
        c_x_list = [c_x]
        for start, end, avg_x in final_scenes[1:]:
            if start <= c_end:
                c_end = max(c_end, end)
                c_x_list.append(avg_x)
            else:
                m_x = sum(c_x_list) / len(c_x_list)
                result.append((c_start, c_end, m_x))
                c_start, c_end = start, end
                c_x_list = [avg_x]
                
        m_x = sum(c_x_list) / len(c_x_list)
        result.append((c_start, c_end, m_x))

        return result

    def _detect_silences(self, video_path: Path, buffer_ms: int = 300) -> List[Tuple[float, float]]:
        silences = []
        try:
            d_sec = buffer_ms / 1000.0
            cmd = [
                str(self.ffmpeg_path),
                '-i', str(video_path),
                '-af', f'silencedetect=noise=-30dB:d={d_sec}',
                '-f', 'null', '-'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            output = result.stderr
            import re
            starts = re.findall(r'silence_start:\s*([\d\.]+)', output)
            ends = re.findall(r'silence_end:\s*([\d\.]+)', output)
            
            for s, e in zip(starts, ends):
                silences.append((float(s), float(e)))
        except Exception as e:
            logging.error(f"VAD Silence Detection failed: {e}")
            
        return silences

    def _extract_audio_embedding(self, video_path: Path, start_time: float, end_time: float) -> np.ndarray:
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                temp_wav_path = temp_wav.name
            
            dur = end_time - start_time
            if dur <= 0: return None
            
            cmd = [
                self.ffmpeg_path,
                "-y", "-ss", str(start_time), "-t", str(dur),
                "-i", str(video_path),
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                temp_wav_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if not os.path.exists(temp_wav_path):
                return None
            
            with wave.open(temp_wav_path, "rb") as wf:
                rate = wf.getframerate()
                sig = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
            os.remove(temp_wav_path)
            
            if len(sig) == 0:
                return None
                
            mfcc_feat = python_speech_features.mfcc(sig, rate)
            # Compute mean MFCC vector across time
            return np.mean(mfcc_feat, axis=0)
        except Exception as e:
            logging.error(f"Failed to extract audio embedding: {e}")
            return None

    def _build_target_voice_print(self, video_path: Path, intervals: List[Tuple[float, float, float]]) -> np.ndarray:
        # Sort intervals by duration to pick the longest continuous scenes of the character
        sorted_intervals = sorted(intervals, key=lambda x: x[1] - x[0], reverse=True)
        embeddings = []
        # Take up to top 3 longest intervals
        for s, e, _ in sorted_intervals[:3]:
            dur = e - s
            if dur < 0.5:
                continue
            # Extract embedding from the middle portion to avoid cuts
            test_s = s + (dur / 2) - min(1.0, dur / 2)
            test_e = test_s + min(2.0, dur)
            emb = self._extract_audio_embedding(video_path, test_s, test_e)
            if emb is not None:
                embeddings.append(emb)
                
        if len(embeddings) > 0:
            # Average the embeddings to build the Voice Print
            return np.mean(embeddings, axis=0)
        return None

    def _check_lip_movement(self, video_path: Path, timestamp: float, target_encoding: np.ndarray, duration_sec: float = 0.5) -> bool:
        if self.mode != "Real Faces" or target_encoding is None:
            return True # Cannot do 68-point landmarks on anime faces
            
        import face_recognition
        import numpy as np
        
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 24
        
        cap.set(cv2.CAP_PROP_POS_MSEC, max(0, timestamp) * 1000)
        frames_to_check = max(5, int(duration_sec * fps))
        mouth_distances = []
        
        for _ in range(frames_to_check):
            ret, frame = cap.read()
            if not ret:
                break
                
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame, model="hog")
            if not face_locations:
                continue
                
            encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            for loc, enc in zip(face_locations, encodings):
                match = face_recognition.compare_faces([target_encoding], enc, tolerance=0.5)[0]
                if match:
                    landmarks = face_recognition.face_landmarks(rgb_frame, [loc])
                    if landmarks and 'top_lip' in landmarks[0] and 'bottom_lip' in landmarks[0]:
                        top_lip = landmarks[0]['top_lip']
                        bottom_lip = landmarks[0]['bottom_lip']
                        top_y = sum([p[1] for p in top_lip]) / len(top_lip)
                        bottom_y = sum([p[1] for p in bottom_lip]) / len(bottom_lip)
                        mouth_distances.append(abs(bottom_y - top_y))
                    break
        cap.release()
        
        if len(mouth_distances) > 2:
            variance = np.var(mouth_distances)
            return variance > 1.5
            
        return False

    def find_scenes(self, video_path: Path, ref_data, padding_before: float, padding_after: float, max_gap_tolerance: float = 1.5, min_scene_duration: float = 1.0) -> List[Tuple[float, float]]:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise IOError(f"Could not open video file: {video_path}")

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if fps <= 0 or total_frames <= 0:
                logging.warning("Could not determine FPS or total frames accurately.")
                if fps <= 0: fps = 24.0
                if total_frames <= 0: total_frames = 1000

            frame_count = 0
            timestamps = []
            
            cascade = None
            profile_cascade = None
            if self.mode == "Anime":
                self.log_queue.put(("log", "Note: Anime mode detects all faces in the frame, not a specific character."))
                self._download_anime_cascade()
                cascade = cv2.CascadeClassifier(str(self.anime_cascade_path))
                if cascade.empty():
                    raise RuntimeError("Failed to load anime face cascade XML. File may be missing or corrupted.")
            elif self.mode == "Real Faces":
                profile_cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_profileface.xml')
                profile_cascade = cv2.CascadeClassifier(profile_cascade_path)

            logging.info(f"Starting facial recognition scan in {self.mode} mode...")
            start_time = time.time()
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if frame_count % self.frame_skip == 0:
                    progress = frame_count / total_frames
                    elapsed = time.time() - start_time
                    eta_seconds = (elapsed / progress) - elapsed if progress > 0 else 0
                        
                    eta_mins = int(eta_seconds // 60)
                    eta_secs = int(eta_seconds % 60)
                    
                    self.log_queue.put(("progress", progress, f"ETA: {eta_mins}m {eta_secs}s  ({int(progress*100)}%)"))
                    
                    processed_frames = frame_count // self.frame_skip
                    if processed_frames > 0 and processed_frames % 50 == 0:
                        logging.info(f"Scanning frame {frame_count}/{total_frames}...")
                    
                    if self.mode == "Real Faces":
                        h, w = frame.shape[:2]
                        if w > 480:
                            ratio = 480.0 / w
                            new_h = int(h * ratio)
                            small_frame = cv2.resize(frame, (480, new_h))
                        else:
                            small_frame = frame
                            
                        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                        face_locations = face_recognition.face_locations(rgb_frame, model="hog")
                        
                        if not face_locations and profile_cascade and not profile_cascade.empty():
                            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                            
                            profiles_right = profile_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                            for (x, y, w, h) in profiles_right:
                                face_locations.append((y, x+w, y+h, x))
                                
                            flipped_gray = cv2.flip(gray, 1)
                            profiles_left = profile_cascade.detectMultiScale(flipped_gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                            h_img, w_img = gray.shape
                            for (x, y, w, h) in profiles_left:
                                x_real = w_img - (x + w)
                                face_locations.append((y, x_real+w, y+h, x_real))
                                
                        if face_locations:
                            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                            
                            for idx, encoding in enumerate(face_encodings):
                                matches = face_recognition.compare_faces([ref_data], encoding, tolerance=self.tolerance)
                                if matches[0]:
                                    top, right, bottom, left = face_locations[idx]
                                    center_x = (left + right) / 2.0
                                    w_resized = small_frame.shape[1]
                                    rel_x = center_x / w_resized
                                    timestamps.append((frame_count / fps, rel_x))
                                    break 
                                
                    elif self.mode == "Anime":
                        h, w = frame.shape[:2]
                        if w > 480:
                            ratio = 480.0 / w
                            new_h = int(h * ratio)
                            small_frame = cv2.resize(frame, (480, new_h))
                        else:
                            small_frame = frame
                            
                        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(24, 24))
                        
                        if len(faces) > 0:
                            (x_f, y_f, w_f, h_f) = faces[0]
                            center_x = x_f + w_f / 2.0
                            w_resized = small_frame.shape[1]
                            rel_x = center_x / w_resized
                            timestamps.append((frame_count / fps, rel_x))
                
                frame_count += 1
        finally:
            cap.release()
        
        # Ensure progress reaches 100%
        self.log_queue.put(("progress", 1.0, "Scan Complete"))

        duration = self._get_video_duration(video_path)
        merged_intervals = self.merge_intervals(timestamps, padding_before, padding_after, duration, max_gap_tolerance, min_scene_duration)
        
        return merged_intervals

    def extract_and_concat(self, video_path: Path, intervals: List[Tuple[float, float, float]], output_path: Path, aspect_ratio: str = "16:9 Original"):
        if not intervals:
            logging.warning("No scenes to extract.")
            return

        temp_dir = Path(tempfile.mkdtemp(prefix="scenepack_tmp_"))
        concat_list_path = temp_dir / "concat_list.txt"
        
        try:
            codec, extra_args = self._get_best_video_codec_and_args()
            logging.info(f"Extracting scenes in parallel via FFmpeg (codec: {codec})...")
            if hasattr(self, "log_queue") and self.log_queue:
                self.log_queue.put(("log", f"Rendering with Hardware Acceleration: using video encoder '{codec}'."))

            total_segments = len(intervals)
            completed_count = 0
            count_lock = threading.Lock()

            def process_segment(index_and_interval):
                nonlocal completed_count
                i, (start, end, avg_x) = index_and_interval
                chunk_path = temp_dir / f"chunk_{i:04d}.ts"
                duration = end - start
                
                # Determine video filter based on aspect ratio
                vf_filter = "setpts=PTS-STARTPTS,fps=24"
                if "9:16 Vertical (Auto-Track)" in aspect_ratio:
                    # Crop logic: height remains the same, width is ih*(9/16).
                    # We ensure even dimensions using ceil(ih*9/32)*2 to prevent YUV420p odd-dimension black lines.
                    vf_filter = f"crop='ceil(ih*9/32)*2':'ceil(ih/2)*2':'iw*{avg_x}-ceil(ih*9/32)':0,setpts=PTS-STARTPTS,fps=24"
                elif "9:16 Blurred Background" in aspect_ratio:
                    # Blurred background: scale original to 9:16 keeping aspect ratio for foreground,
                    # scale background to fill 9:16, apply blur, overlay. Ensured even dimensions.
                    vf_filter = "[0:v]split=2[fg][bg];[bg]scale='ceil(ih*9/32)*2':'ceil(ih/2)*2':force_original_aspect_ratio=increase,crop='ceil(ih*9/32)*2':'ceil(ih/2)*2',boxblur=20:20[bg2];[fg]scale='ceil(ih*9/32)*2':'ceil(ih/2)*2':force_original_aspect_ratio=decrease[fg2];[bg2][fg2]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2,setpts=PTS-STARTPTS,fps=24"

                cmd = [
                    str(self.ffmpeg_path), '-y', 
                    '-hide_banner', '-loglevel', 'error',
                    '-ss', str(start), 
                    '-accurate_seek',
                    '-i', str(video_path), 
                    '-t', str(duration), 
                    '-fps_mode', 'cfr'
                ]
                
                if "Blurred Background" in aspect_ratio:
                    cmd.extend(['-filter_complex', vf_filter])
                else:
                    cmd.extend(['-vf', vf_filter])
                
                cmd.extend([
                    '-af', 'aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,aresample=async=1,apad',
                    '-c:v', codec,
                ] + extra_args + [
                    '-b:v', '6M',
                    '-g', '24',
                    '-keyint_min', '24',
                    '-bf', '0',
                    '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-ar', '48000',
                    '-ac', '2',
                    '-avoid_negative_ts', 'make_zero',
                    '-max_muxing_queue_size', '2048',
                    str(chunk_path)
                ])

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logging.error(f"FFmpeg slice failed for segment {i+1}: {result.stderr}")
                    return i, None

                with count_lock:
                    completed_count += 1
                    if completed_count % max(1, total_segments // 10) == 0 or completed_count == total_segments:
                        logging.info(f"Completed {completed_count}/{total_segments} segments...")

                return i, chunk_path

            max_workers = min(8, os.cpu_count() or 4)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(process_segment, enumerate(intervals)))

            # Sort by original chronological order
            results.sort(key=lambda x: x[0])

            with open(concat_list_path, "w") as f:
                for i, chunk_path in results:
                    if chunk_path and chunk_path.exists():
                        safe_name = chunk_path.name.replace("'", "'\\''")
                        f.write(f"file '{safe_name}'\n")

            logging.info("Concatenating extracted scenes...")
            concat_cmd = [
                str(self.ffmpeg_path), '-y', 
                '-hide_banner', '-loglevel', 'error',
                '-f', 'concat', 
                '-safe', '0', 
                '-i', str(concat_list_path),
                '-c', 'copy',
                '-bsf:a', 'aac_adtstoasc',
                '-fflags', '+genpts+discardcorrupt',
                '-movflags', '+faststart',
                str(output_path)
            ]
            
            concat_result = subprocess.run(concat_cmd, cwd=temp_dir, capture_output=True, text=True)
            if concat_result.returncode != 0:
                raise RuntimeError(f"FFmpeg concat failed: {concat_result.stderr}")
                
            logging.info(f"Successfully saved scenepack to:\n{output_path.name}")

        finally:
            logging.info("Cleaning up temporary chunk files...")
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _detect_scene_cuts(self, video_path: Path, threshold: float = 0.3) -> List[float]:
        cuts = []
        try:
            cmd = [
                str(self.ffmpeg_path),
                '-i', str(video_path),
                '-vf', f"select='gt(scene,{threshold})',showinfo",
                '-f', 'null', '-'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            output = result.stderr
            import re
            # Extract pts_time from showinfo filter output
            pts_times = re.findall(r'pts_time:\s*([\d\.]+)', output)
            cuts = [float(pt) for pt in pts_times]
        except Exception as e:
            logging.error(f"Scene cut detection failed: {e}")
        return cuts

    def scan_and_prepare(self, video_path: Path, ref_image_path: Path, padding_before: float = 2.0, padding_after: float = 2.0, max_gap_tolerance: float = 1.5, min_scene_duration: float = 1.0, vad_enabled: bool = False, vad_buffer: int = 300, vad_speaker_enabled: bool = True, vad_speaker_threshold: float = 0.68) -> List[Tuple[float, float, float]]:
        self._check_and_download_ffmpeg()
        
        if not video_path.is_file():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        ref_data = self.load_reference_face(ref_image_path)
        intervals = self.find_scenes(video_path, ref_data, padding_before, padding_after, max_gap_tolerance, min_scene_duration)
        
        logging.info("Detecting shot boundaries for scene snapping...")
        scene_cuts = self._detect_scene_cuts(video_path)
        
        # Apply VAD & Lip-sync
        if vad_enabled:
            logging.info("VAD Protection Enabled. Running FFmpeg silence detection...")
            silences = self._detect_silences(video_path, vad_buffer)
            if silences:
                logging.info(f"Detected {len(silences)} silence intervals. Snapping boundaries...")
                refined_intervals = []
                for start, end, avg_x in intervals:
                    new_start, new_end = start, end
                    
                    # Snap end
                    if not any(s <= end <= e for s, e in silences):
                        next_silences = [s for s, e in silences if s >= end]
                        if next_silences:
                            is_speaking = self._check_lip_movement(video_path, end - 0.2, ref_data)
                            if is_speaking:
                                logging.info(f"Lip-Sync: Extending {end:.2f}s to {next_silences[0]:.2f}s.")
                                new_end = next_silences[0]
                                
                    # Snap start
                    if not any(s <= start <= e for s, e in silences):
                        prev_silences = [e for s, e in silences if e <= start]
                        if prev_silences:
                            is_speaking_start = self._check_lip_movement(video_path, start, ref_data)
                            if is_speaking_start:
                                logging.info(f"Lip-Sync: Pulling {start:.2f}s back to {prev_silences[-1]:.2f}s.")
                                new_start = prev_silences[-1]
                                
                    refined_intervals.append((max(0.0, new_start), new_end, avg_x))
                
                # Merge overlaps created by extending
                final_intervals = []
                for s, e, avg_x in refined_intervals:
                    if not final_intervals:
                        final_intervals.append((s, e, avg_x))
                    else:
                        prev_s, prev_e, prev_avg_x = final_intervals[-1]
                        if s <= prev_e:
                            final_intervals[-1] = (prev_s, max(prev_e, e), (prev_avg_x + avg_x) / 2.0)
                        else:
                            final_intervals.append((s, e, avg_x))
                intervals = final_intervals
                
                # Target Speaker Voice Matching (Voice Fingerprinting)
                if vad_speaker_enabled and len(intervals) > 0:
                    logging.info("Target Speaker Voice Matching Enabled. Enrolling Target Voice Print...")
                    voice_print = self._build_target_voice_print(video_path, intervals)
                    if voice_print is not None:
                        logging.info(f"Target Voice Enrolled. Verifying speakers across {len(intervals)} clips...")
                        verified_intervals = []
                        for s, e, avg_x in intervals:
                            # Use only the middle 2 seconds of the clip (or less if short) to avoid intro/outro noise
                            dur = e - s
                            if dur < 0.2:
                                continue
                            test_s = s + (dur / 2) - min(1.0, dur / 2)
                            test_e = test_s + min(2.0, dur)
                            emb = self._extract_audio_embedding(video_path, test_s, test_e)
                            if emb is not None:
                                norm_vp = np.linalg.norm(voice_print)
                                norm_emb = np.linalg.norm(emb)
                                sim = 0.0
                                if norm_vp > 0 and norm_emb > 0:
                                    sim = np.dot(voice_print, emb) / (norm_vp * norm_emb)
                                
                                if sim >= vad_speaker_threshold:
                                    logging.info(f"Clip [{s:.2f}-{e:.2f}] Verified (Similarity: {sim:.3f} >= {vad_speaker_threshold})")
                                    verified_intervals.append((s, e, avg_x))
                                else:
                                    logging.warning(f"Clip [{s:.2f}-{e:.2f}] Discarded! Background/Narrator detected (Similarity: {sim:.3f} < {vad_speaker_threshold})")
                            else:
                                verified_intervals.append((s, e, avg_x)) # Keep if audio extraction failed or no voice
                        intervals = verified_intervals
                    else:
                        logging.warning("Failed to build Target Voice Print. Skipping speaker verification.")

        # Apply Scene Cut Snapping
        snapped_intervals = []
        for start, end, avg_x in intervals:
            new_start, new_end = start, end
            # Snap start to nearest cut within 1.0s
            nearest_start_cut = next((c for c in scene_cuts if abs(c - start) <= 1.0), None)
            if nearest_start_cut is not None:
                logging.info(f"Snapping start {start:.2f}s to shot boundary {nearest_start_cut:.2f}s")
                new_start = nearest_start_cut
            
            # Snap end to nearest cut within 1.0s
            nearest_end_cut = next((c for c in scene_cuts if abs(c - end) <= 1.0), None)
            if nearest_end_cut is not None:
                logging.info(f"Snapping end {end:.2f}s to shot boundary {nearest_end_cut:.2f}s")
                new_end = nearest_end_cut
                
            snapped_intervals.append((new_start, new_end, avg_x))
        intervals = snapped_intervals
        
        logging.info(f"Found {len(intervals)} contiguous scene(s) after merging overlaps.")
        for start, end, avg_x in intervals:
            logging.info(f"  -> Scene: {start:.2f}s to {end:.2f}s (Face X: {avg_x:.2f})")
            
        if not intervals:
            raise ValueError("Target face was not detected in the video. Aborting.")

        return intervals


class FocusApp(ctk.CTk):
    def __init__(self):
        super().__init__(className="Focus")
        
        self.title(f"Focus - Automated Facial Scenepack Generator ({APP_VERSION})")
        self.geometry("950x750")
        
        if platform.system() == "Windows":
            self.settings_file = Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / "Focus" / ".scenepack_generator_settings.json"
        else:
            self.settings_file = Path.home() / ".scenepack_generator_settings.json"
        self.settings = self.load_settings()
        
        # Variables - Declare ALL Tkinter variables right after loading settings!
        self.video_path_var = ctk.StringVar(value="No video selected")
        self.image_path_var = ctk.StringVar(value="No image selected")
        self.output_path_var = ctk.StringVar(value="No save location selected")
        
        self.pad_before_var = ctk.StringVar(value=str(self.settings.get("pad_before", 2.0)))
        self.pad_after_var = ctk.StringVar(value=str(self.settings.get("pad_after", 2.0)))
        self.max_gap_var = ctk.StringVar(value=str(self.settings.get("max_gap_tolerance", 1.5)))
        self.min_scene_var = ctk.StringVar(value=str(self.settings.get("min_scene_duration", 1.0)))
        self.frame_skip_var = ctk.StringVar(value=str(self.settings.get("frame_skip", 15)))
        self.vad_enabled_var = ctk.BooleanVar(value=self.settings.get("vad_enabled", True))
        self.vad_buffer_var = ctk.StringVar(value=str(self.settings.get("vad_buffer", 300)))
        
        self.vad_speaker_enabled_var = ctk.BooleanVar(value=self.settings.get("vad_speaker_enabled", True))
        self.vad_speaker_threshold_var = ctk.DoubleVar(value=self.settings.get("vad_speaker_threshold", 0.68))
        self.play_sound_var = ctk.BooleanVar(value=self.settings.get("play_sound", True))
        self._cancel_gallery_scan = False
        self._target_progress = 0.0
        self._is_scanning = False
        self._is_rendering = False

        self.app_dir = Path(os.path.expanduser('~/Library/Application Support/Focus'))
        self.app_dir.mkdir(parents=True, exist_ok=True)
        self.anime_cascade_path = self.app_dir / "lbpcascade_animeface.xml"
        
        # UI/UX Redesign: Modern Dark-Mode Dashboard aesthetic
        current_appearance = self.settings.get("appearance_mode", "Dark")
        current_theme = self.settings.get("color_theme", "blue")
        current_language = self.settings.get("language", "English")
        
        # Override window background to deep dark color
        self.configure(fg_color=("#F2F2F7", "#0B0C0E"))
        
        ctk.set_appearance_mode(current_appearance)
        self._apply_theme(current_theme)
        
        # Dynamic macOS Dock & Window Icon Setup
        self.update_dynamic_app_icon(current_theme, current_appearance)
            
        # Grid Layout (1 row, 2 columns)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # --- SIDEBAR (Column 0) ---
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=("#FFFFFF", "#14161B"))
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(11, weight=1) # Spacer
        self.sidebar_frame.grid_columnconfigure(0, weight=1) # Prevent grid collapse
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Focus", font=ctk.CTkFont(size=28, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(25, 20), sticky="w")
        
        # SECTION: WORKFLOW
        lbl_workflow = ctk.CTkLabel(self.sidebar_frame, text="WORKFLOW", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray50")
        lbl_workflow.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.btn_tutorial = ctk.CTkButton(self.sidebar_frame, text="How to Use", command=self.open_tutorial, corner_radius=15, fg_color="transparent", hover_color=("#D1D1D6", "#1C1F26"), anchor="w")
        self.btn_tutorial.grid(row=2, column=0, padx=15, pady=2, sticky="ew")
        
        self.btn_changelog = ctk.CTkButton(self.sidebar_frame, text="Changelog", command=self.open_changelog, corner_radius=15, fg_color="transparent", hover_color=("#D1D1D6", "#1C1F26"), anchor="w")
        self.btn_changelog.grid(row=3, column=0, padx=15, pady=2, sticky="ew")

        # SECTION: SYSTEM
        lbl_system = ctk.CTkLabel(self.sidebar_frame, text="SYSTEM", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray50")
        lbl_system.grid(row=4, column=0, padx=20, pady=(20, 5), sticky="w")
        
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w", font=ctk.CTkFont(size=12))
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(5, 0), sticky="ew")
        self.appearance_mode_optionemenu = ctk.CTkSegmentedButton(self.sidebar_frame, values=["Light", "Dark", "System"], command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=15, pady=(5, 10), sticky="ew")
        self.appearance_mode_optionemenu.set(current_appearance)
        
        self.color_theme_label = ctk.CTkLabel(self.sidebar_frame, text="Color Theme:", anchor="w", font=ctk.CTkFont(size=12))
        self.color_theme_label.grid(row=7, column=0, padx=20, pady=(5, 0), sticky="ew")
        self.color_theme_optionmenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["red", "orange", "yellow", "green", "blue", "indigo", "violet", "pink"], command=self.change_theme_event)
        self.color_theme_optionmenu.grid(row=8, column=0, padx=15, pady=(5, 10), sticky="ew")
        self.color_theme_optionmenu.set(current_theme)

        self.language_label = ctk.CTkLabel(self.sidebar_frame, text="Language:", anchor="w", font=ctk.CTkFont(size=12))
        self.language_label.grid(row=9, column=0, padx=20, pady=(5, 0), sticky="ew")
        self.language_optionmenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Polski", "English", "Deutsch", "Русский", "Українська", "Español", "Français", "日本語"], command=self.change_language_event)
        self.language_optionmenu.grid(row=10, column=0, padx=15, pady=(5, 10), sticky="ew")
        self.language_optionmenu.set(current_language)
        
        self.sound_switch = ctk.CTkSwitch(self.sidebar_frame, text="Play sound on complete", variable=self.play_sound_var, command=self.save_current_settings)
        self.sound_switch.grid(row=12, column=0, padx=20, pady=(10, 20), sticky="w")
        
        # --- MAIN CONTAINER (Column 1) ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=30, pady=20)
        
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, 15))
        
        self.dashboard_label = ctk.CTkLabel(self.header_frame, text="Dashboard", font=ctk.CTkFont(family="Helvetica", size=26, weight="bold"))
        self.dashboard_label.pack(side="left", padx=(0, 15))
        
        self.mode_var = ctk.StringVar(value="Real Faces")
        self.mode_switch = ctk.CTkSegmentedButton(self.header_frame, values=["Real Faces", "Anime"], variable=self.mode_var, command=self._on_mode_switched)
        self.mode_switch.pack(side="right", ipadx=10, ipady=5)
        
        self.tab_view_var = ctk.StringVar(value="Generator")
        self.tab_switcher = ctk.CTkSegmentedButton(self.header_frame, values=["Generator", "Beta / Character Gallery"], variable=self.tab_view_var, command=self._switch_main_view)
        self.tab_switcher.pack(side="left", ipadx=8, ipady=4)
        
        self.after(200, self._add_mode_tooltips)
        
        # Generator View Container
        self.generator_view = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        self.generator_view.pack(fill="both", expand=True)

        # HERO BANNER
        theme_hex = THEME_COLORS.get(current_theme, THEME_COLORS["blue"])
        self.hero_banner = ctk.CTkFrame(self.generator_view, corner_radius=16, fg_color=("#FFFFFF", "#14161B"), border_width=2, border_color=theme_hex)
        self.hero_banner.pack(fill="x", pady=(0, 15), ipady=10)
        
        hero_title = ctk.CTkLabel(self.hero_banner, text="Focus - AI Scenepack Generator", font=ctk.CTkFont(size=22, weight="bold"))
        hero_title.pack(anchor="w", padx=20, pady=(15, 0))
        hero_sub = ctk.CTkLabel(self.hero_banner, text="Automated facial tracking and intelligent clip extraction.", text_color="gray60", font=ctk.CTkFont(size=14))
        hero_sub.pack(anchor="w", padx=20, pady=(0, 15))

        # 2. Settings Frame (Preset Bar + 10 columns for entries)
        self.frame_settings = ctk.CTkFrame(self.generator_view, corner_radius=16, fg_color=("#FFFFFF", "#14161B"))
        self.frame_settings.pack(fill="x", pady=10)

        # Top Bar: Presets & Smart Auto-Tune
        self.frame_top_settings = ctk.CTkFrame(self.frame_settings, fg_color="transparent")
        self.frame_top_settings.pack(fill="x", padx=15, pady=(12, 5))

        self.lbl_preset = ctk.CTkLabel(self.frame_top_settings, text="Preset Profiles:", font=ctk.CTkFont(weight="bold"))
        self.lbl_preset.pack(side="left", padx=(0, 10))

        self.preset_var = ctk.StringVar(value="✨ Auto-Tune (Recommended)")
        self.preset_menu = ctk.CTkOptionMenu(
            self.frame_top_settings,
            values=[
                "✨ Auto-Tune (Recommended)",
                "⚡ Fast / Short Edits (TikTok/Reels)",
                "🎬 Cinematic / Long Scenes",
                "🚀 Ultra-Fast Scan (Draft)"
            ],
            variable=self.preset_var,
            command=self._on_preset_selected,
            width=260,
            corner_radius=8,
        )
        self.preset_menu.pack(side="left", padx=(0, 15))

        self.btn_auto_tune = ctk.CTkButton(
            self.frame_top_settings,
            text="✨ Auto-Tune",
            command=self.apply_auto_tune,
            width=120,
            corner_radius=8,
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            font=ctk.CTkFont(weight="bold")
        )
        self.btn_auto_tune.pack(side="left", padx=(0, 15))

        self.aspect_ratio_var = ctk.StringVar(value="16:9 Original")
        self.aspect_ratio_menu = ctk.CTkOptionMenu(
            self.frame_top_settings,
            values=[
                "16:9 Original",
                "9:16 Vertical (Auto-Track)",
                "9:16 Blurred Background"
            ],
            variable=self.aspect_ratio_var,
            width=220,
            corner_radius=8,
        )
        self.aspect_ratio_menu.pack(side="left", padx=(0, 15))

        # Bottom Bar: Parameter Input Entries
        self.frame_entry_settings = ctk.CTkFrame(self.frame_settings, fg_color="transparent")
        self.frame_entry_settings.pack(fill="x", padx=10, pady=(5, 12))
        for i in range(10):
            self.frame_entry_settings.grid_columnconfigure(i, weight=1)
            
        self.lbl_pad_before = ctk.CTkLabel(self.frame_entry_settings, text="Padding Before (s):")
        self.lbl_pad_before.grid(row=0, column=0, padx=(10, 2), pady=8)
        entry_pad_before = ctk.CTkEntry(self.frame_entry_settings, textvariable=self.pad_before_var, width=48, corner_radius=8)
        entry_pad_before.grid(row=0, column=1, padx=2, pady=8)
        
        self.lbl_pad_after = ctk.CTkLabel(self.frame_entry_settings, text="Padding After (s):")
        self.lbl_pad_after.grid(row=0, column=2, padx=2, pady=8)
        entry_pad_after = ctk.CTkEntry(self.frame_entry_settings, textvariable=self.pad_after_var, width=48, corner_radius=8)
        entry_pad_after.grid(row=0, column=3, padx=2, pady=8)

        self.lbl_max_gap = ctk.CTkLabel(self.frame_entry_settings, text="Max Gap Tolerance (s):")
        self.lbl_max_gap.grid(row=0, column=4, padx=2, pady=8)
        entry_max_gap = ctk.CTkEntry(self.frame_entry_settings, textvariable=self.max_gap_var, width=48, corner_radius=8)
        entry_max_gap.grid(row=0, column=5, padx=2, pady=8)

        self.lbl_min_scene = ctk.CTkLabel(self.frame_entry_settings, text="Min Scene Length (s):")
        self.lbl_min_scene.grid(row=0, column=6, padx=2, pady=8)
        entry_min_scene = ctk.CTkEntry(self.frame_entry_settings, textvariable=self.min_scene_var, width=48, corner_radius=8)
        entry_min_scene.grid(row=0, column=7, padx=2, pady=8)
        
        self.lbl_frame_skip = ctk.CTkLabel(self.frame_entry_settings, text="Frame Skip Interval:")
        self.lbl_frame_skip.grid(row=0, column=8, padx=2, pady=8)
        entry_frame_skip = ctk.CTkEntry(self.frame_entry_settings, textvariable=self.frame_skip_var, width=48, corner_radius=8)
        entry_frame_skip.grid(row=0, column=9, padx=(2, 10), pady=8)

        # Row 1 for VAD parameters
        self.cb_vad_enabled = ctk.CTkCheckBox(self.frame_entry_settings, text="Smart Sentence Protection (VAD & Lip-Sync):", variable=self.vad_enabled_var)
        self.cb_vad_enabled.grid(row=1, column=0, columnspan=6, padx=(10, 2), pady=8, sticky="w")
        
        self.lbl_vad_buffer = ctk.CTkLabel(self.frame_entry_settings, text="Silence Snapping Buffer (ms):")
        self.lbl_vad_buffer.grid(row=1, column=6, columnspan=2, padx=2, pady=8, sticky="e")
        entry_vad_buffer = ctk.CTkEntry(self.frame_entry_settings, textvariable=self.vad_buffer_var, width=48, corner_radius=8)
        entry_vad_buffer.grid(row=1, column=8, columnspan=2, padx=(2, 10), pady=8, sticky="w")
        
        # Row 2 for Voice Fingerprinting parameters
        self.cb_vad_speaker_enabled = ctk.CTkCheckBox(self.frame_entry_settings, text="Target Speaker Voice Matching:", variable=self.vad_speaker_enabled_var)
        self.cb_vad_speaker_enabled.grid(row=2, column=0, columnspan=6, padx=(10, 2), pady=8, sticky="w")
        
        self.lbl_vad_speaker_threshold = ctk.CTkLabel(self.frame_entry_settings, text="Voice Similarity Threshold:")
        self.lbl_vad_speaker_threshold.grid(row=2, column=6, columnspan=2, padx=2, pady=8, sticky="e")
        self.slider_vad_speaker_threshold = ctk.CTkSlider(self.frame_entry_settings, from_=0.50, to=0.90, number_of_steps=40, variable=self.vad_speaker_threshold_var, width=120)
        self.slider_vad_speaker_threshold.grid(row=2, column=8, columnspan=2, padx=(2, 10), pady=8, sticky="w")

        self.tt_pad_before = ToolTip(self.lbl_pad_before, "")
        self.tt_pad_before_entry = ToolTip(entry_pad_before, "")
        self.tt_pad_after = ToolTip(self.lbl_pad_after, "")
        self.tt_pad_after_entry = ToolTip(entry_pad_after, "")
        self.tt_max_gap = ToolTip(self.lbl_max_gap, "")
        self.tt_max_gap_entry = ToolTip(entry_max_gap, "")
        self.tt_min_scene = ToolTip(self.lbl_min_scene, "")
        self.tt_min_scene_entry = ToolTip(entry_min_scene, "")
        self.tt_frame_skip = ToolTip(self.lbl_frame_skip, "")
        self.tt_frame_skip_entry = ToolTip(entry_frame_skip, "")
        self.tt_vad_enabled = ToolTip(self.cb_vad_enabled, "")
        self.tt_vad_buffer = ToolTip(self.lbl_vad_buffer, "")
        self.tt_vad_buffer_entry = ToolTip(entry_vad_buffer, "")
        self.tt_vad_speaker_enabled = ToolTip(self.cb_vad_speaker_enabled, "")
        self.tt_vad_speaker_threshold = ToolTip(self.lbl_vad_speaker_threshold, "")
        self.tt_vad_speaker_threshold_slider = ToolTip(self.slider_vad_speaker_threshold, "")
        
        self.frame_files = ctk.CTkFrame(self.generator_view, corner_radius=16, fg_color=("#FFFFFF", "#14161B"))
        self.frame_files.pack(fill="x", pady=10, ipady=10)
        self.frame_files.grid_columnconfigure(1, weight=1)
        
        btn_font = ctk.CTkFont(weight="bold")
        
        self.btn_sel_video = ctk.CTkButton(self.frame_files, text="Select Input Video", command=self.select_video, font=btn_font, corner_radius=8)
        self.btn_sel_video.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        ctk.CTkLabel(self.frame_files, textvariable=self.video_path_var, anchor="w", corner_radius=8).grid(row=0, column=1, padx=(0, 20), pady=15, sticky="ew")
        
        self.btn_sel_ref = ctk.CTkButton(self.frame_files, text="Select Reference Face", command=self.select_image, font=btn_font, corner_radius=8)
        self.btn_sel_ref.grid(row=1, column=0, padx=20, pady=15, sticky="w")
        ctk.CTkLabel(self.frame_files, textvariable=self.image_path_var, anchor="w", corner_radius=8).grid(row=1, column=1, padx=(0, 20), pady=15, sticky="ew")
        
        self.btn_sel_output = ctk.CTkButton(self.frame_files, text="Select Save Location", command=self.select_output, font=btn_font, corner_radius=8)
        self.btn_sel_output.grid(row=2, column=0, padx=20, pady=15, sticky="w")
        ctk.CTkLabel(self.frame_files, textvariable=self.output_path_var, anchor="w", corner_radius=8).grid(row=2, column=1, padx=(0, 20), pady=15, sticky="ew")
        
        # Progress and ETA Frame
        self.frame_progress = ctk.CTkFrame(self.generator_view, fg_color="transparent")
        self.frame_progress.pack(fill="x", pady=(10, 0))
        
        self.progress_bar = ctk.CTkProgressBar(self.frame_progress, height=12, corner_radius=6)
        self.progress_bar.pack(fill="x", pady=(0, 5))
        self.progress_bar.set(0)
        
        self.eta_label = ctk.CTkLabel(self.frame_progress, text="Ready to generate", text_color="gray60")
        self.eta_label.pack()
        
        # 3. Generate Button
        self.btn_generate = ctk.CTkButton(self.generator_view, text="1. Scan & Analyze Video", command=self.start_scan, height=55, font=ctk.CTkFont(family="Helvetica", size=18, weight="bold"), corner_radius=12)
        self.btn_generate.pack(fill="x", pady=20)

        # 4. Review Results Frame
        self.frame_review = ctk.CTkFrame(self.generator_view, corner_radius=15, fg_color=("gray85", "gray15"), height=0)
        self.frame_review.pack_propagate(False)
        self.frame_review.pack(fill="both", expand=True, pady=5)
        
        self.lbl_review = ctk.CTkLabel(self.frame_review, text="Interactive Clip Review:", font=ctk.CTkFont(weight="bold"))
        self.lbl_review.pack(anchor="w", padx=20, pady=(10, 5))
        
        self.review_scroll_frame = ctk.CTkScrollableFrame(self.frame_review, fg_color="transparent")
        self.review_scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.review_btn_frame = ctk.CTkFrame(self.frame_review, fg_color="transparent")
        self.review_btn_frame.pack(fill="x", padx=20, pady=10)
        
        self.btn_play_orig = ctk.CTkButton(self.review_btn_frame, text="Play Original Video", command=self.play_original, corner_radius=8, fg_color=("#E5E5EA", "#3a3a3a"), hover_color=("#D1D1D6", "#4a4a4a"))
        self.btn_play_orig.pack(side="left", padx=(0, 10))
        
        self.btn_play_scene = ctk.CTkButton(self.review_btn_frame, text="Play Result (If Extracted)", command=self.play_scenepack, corner_radius=8, fg_color=("#007AFF", "#215d9c"), hover_color=("#0056b3", "#2c7ace"))
        self.btn_play_scene.pack(side="left", padx=(0, 10))
        
        self.btn_render = ctk.CTkButton(self.review_btn_frame, text="2. Render Selected Clips", command=self.start_render, height=45, font=ctk.CTkFont(weight="bold"), fg_color=("#34C759", "#28a745"), hover_color=("#28A745", "#218838"))
        self.btn_render.pack(side="right")
        
        # 5. Log Textbox
        self.log_textbox = ctk.CTkTextbox(self.generator_view, state="disabled", wrap="word", font=("Courier", 13), corner_radius=10, fg_color=("gray90", "gray10"))
        self.log_textbox.pack(fill="both", expand=True)

        # Gallery View Container (Initially Unpacked)
        self.gallery_view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        self.gallery_top_frame = ctk.CTkFrame(self.gallery_view, corner_radius=15, fg_color=("gray85", "gray15"))
        self.gallery_top_frame.pack(fill="x", pady=(0, 15), ipadx=10, ipady=10)

        self.lbl_gallery_title = ctk.CTkLabel(self.gallery_top_frame, text="Interactive Character Auto-Gallery (Beta)", font=ctk.CTkFont(family="Helvetica", size=20, weight="bold"))
        self.lbl_gallery_title.pack(anchor="w", padx=20, pady=(15, 2))
        
        self.lbl_gallery_desc = ctk.CTkLabel(self.gallery_top_frame, text="Pre-scan input video to auto-discover unique character faces. Click any card to select as target reference face!", text_color="gray60", anchor="w")
        self.lbl_gallery_desc.pack(anchor="w", padx=20, pady=(0, 15))

        self.gallery_btn_frame = ctk.CTkFrame(self.gallery_top_frame, fg_color="transparent")
        self.gallery_btn_frame.pack(anchor="w", padx=20, pady=(0, 15))

        self.btn_scan_gallery = ctk.CTkButton(self.gallery_btn_frame, text="Scan Video for Characters", command=self.start_gallery_scan, font=btn_font, height=42, corner_radius=10)
        self.btn_scan_gallery.pack(side="left", padx=(0, 10))

        self.btn_cancel_gallery = ctk.CTkButton(self.gallery_btn_frame, text="Cancel Scan", command=self.cancel_gallery_scan, font=btn_font, height=42, corner_radius=10, fg_color=("#FF3B30", "#8b0000"), hover_color=("#D70015", "#a52a2a"), state="disabled")
        self.btn_cancel_gallery.pack(side="left")

        self.gallery_progress_bar = ctk.CTkProgressBar(self.gallery_top_frame, height=10, corner_radius=5)
        self.gallery_progress_bar.pack(fill="x", padx=20, pady=(0, 5))
        self.gallery_progress_bar.set(0)
        
        self.lbl_gallery_status = ctk.CTkLabel(self.gallery_top_frame, text="Ready to scan video", text_color="gray60")
        self.lbl_gallery_status.pack(anchor="w", padx=20, pady=(0, 10))

        self.gallery_scroll_frame = ctk.CTkScrollableFrame(self.gallery_view, label_text="Discovered Characters", corner_radius=15, fg_color=("gray90", "gray10"))
        self.gallery_scroll_frame.pack(fill="both", expand=True)

        self._gallery_card_frames = []
        self._display_gallery_cards([])
        
        # Thread-safe Logging Setup
        self.log_queue = queue.Queue()
        self.log_handler = TextboxLogHandler(self.log_queue)
        self.log_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt="%H:%M:%S"))
        
        # Overwrite standard logger
        logger = logging.getLogger()
        logger.handlers = []
        logger.addHandler(self.log_handler)
        logger.setLevel(logging.INFO)
        
        # Start GUI polling loop
        self.check_log_queue()
        
        # Start Custom Animation Loops
        self._pulse_button_animation()
        self._smooth_progress_update()
        
        # Ensure all UI elements reflect the active color theme upon startup
        self.update_ui_theme_colors(self.settings.get("color_theme", "blue"))

    def _pulse_button_animation(self):
        """Creates a breathing glow effect on the main scan button when idle."""
        if not hasattr(self, 'btn_generate'):
            return
            
        if getattr(self, '_is_scanning', False) or getattr(self, '_is_rendering', False):
            self.btn_generate.configure(border_width=0)
            self.after(500, self._pulse_button_animation)
            return

        import math
        import time
        t = time.time() * 3
        pulse = (math.sin(t) + 1) / 2 # 0 to 1
        
        current_theme = self.settings.get("color_theme", "blue")
        theme_hex = THEME_COLORS.get(current_theme, "#3498DB")
        
        width = int(2 + pulse * 2)
        self.btn_generate.configure(border_width=width, border_color=theme_hex)
        
        self.after(50, self._pulse_button_animation)

    def _smooth_progress_update(self):
        """Interpolates progress bar smoothly to _target_progress."""
        if hasattr(self, 'progress_bar') and hasattr(self, '_target_progress'):
            current = self.progress_bar.get()
            target = getattr(self, '_target_progress', 0.0)
            if abs(current - target) > 0.005:
                new_val = current + (target - current) * 0.15
                self.progress_bar.set(new_val)
            else:
                self.progress_bar.set(target)
        self.after(30, self._smooth_progress_update)

    def _add_mode_tooltips(self):
        try:
            lang_name = self.settings.get("language", "English")
            tt_real = get_translation(lang_name, "tt_real_faces")
            tt_anim = get_translation(lang_name, "tt_anime")

            buttons = getattr(self.mode_switch, '_buttons_dict', {})
            for b_name, btn_widget in buttons.items():
                if not hasattr(btn_widget, '_tooltip_instance'):
                    btn_widget._tooltip_instance = ToolTip(btn_widget, "")
                
                # Assign localized text based on index or name
                if b_name in ["Real Faces", get_translation(lang_name, "real_faces")]:
                    btn_widget._tooltip_instance.set_text(tt_real)
                else:
                    btn_widget._tooltip_instance.set_text(tt_anim)
        except Exception as e:
            logging.debug(f"Could not bind tooltips to segmented button: {e}")

    def open_tutorial(self):
        if hasattr(self, 'tutorial_win') and self.tutorial_win is not None and self.tutorial_win.winfo_exists():
            self.tutorial_win.lift()
            self.tutorial_win.focus_force()
            return

        lang_name = self.settings.get("language", "English")
        tut_title = get_translation(lang_name, "tutorial_title")
        tut_body = get_translation(lang_name, "tutorial_body")
        tut_close = get_translation(lang_name, "tutorial_close")

        self.tutorial_win = ctk.CTkToplevel(self)
        self.tutorial_win.title(f"{tut_title} ({APP_VERSION})")
        self.tutorial_win.geometry("560x400")
        self.tutorial_win.resizable(False, False)
        
        # Explicit fg_color fix for macOS CTkToplevel rendering
        self.tutorial_win.configure(fg_color=ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        
        self.tutorial_win.lift()
        self.tutorial_win.attributes("-topmost", True)
        self.tutorial_win.after(10, lambda: self.tutorial_win.attributes("-topmost", False) if self.tutorial_win.winfo_exists() else None)
        self.tutorial_win.focus_force()

        title = ctk.CTkLabel(self.tutorial_win, text=f"{tut_title} ({APP_VERSION})", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(20, 10))

        textbox = ctk.CTkTextbox(self.tutorial_win, wrap="word", font=ctk.CTkFont(size=14))
        textbox.pack(padx=20, pady=10, fill="both", expand=True)
        textbox.insert("1.0", tut_body)
        textbox.configure(state="disabled")
        
        btn_close = ctk.CTkButton(self.tutorial_win, text=tut_close, command=self.tutorial_win.destroy, width=120)
        btn_close.pack(pady=(5, 15))

    def open_changelog(self):
        if hasattr(self, 'changelog_win') and self.changelog_win is not None and self.changelog_win.winfo_exists():
            self.changelog_win.lift()
            self.changelog_win.focus_force()
            return

        lang_name = self.settings.get("language", "English")
        cl_title = get_translation(lang_name, "changelog_title")
        cl_close = get_translation(lang_name, "changelog_close")

        self.changelog_win = ctk.CTkToplevel(self)
        self.changelog_win.title(f"{cl_title} ({APP_VERSION})")
        self.changelog_win.geometry("600x440")
        self.changelog_win.resizable(False, False)
        
        # Match modern dashboard appearance
        self.changelog_win.configure(fg_color=("#F2F2F7", "#0B0C0E"))
        
        self.changelog_win.lift()
        self.changelog_win.attributes("-topmost", True)
        self.changelog_win.after(10, lambda: self.changelog_win.attributes("-topmost", False) if self.changelog_win.winfo_exists() else None)
        self.changelog_win.focus_force()

        title = ctk.CTkLabel(self.changelog_win, text=f"{cl_title} ({APP_VERSION})", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(20, 10))

        history_text = (
            f"=== Focus {APP_VERSION} Changelog ===\n\n"
            "v0.95 - Consolidated Windows build to a single standalone `Focus.exe` (`--onefile` mode) eliminating redundant launcher files and DLL clutter. Fixed UI color theme persistence by implementing dynamic re-theming across all interactive widgets (buttons, progress bars, borders, sliders, switches) immediately upon theme selection and view navigation without requiring an application restart.\n\n"
            "v0.94 - Fix OpenCV CascadeClassifier & haarcascades missing attribute error in PyInstaller builds (Anime mode & profile detection) by adding full cv2 binary/data collection flags, and added Windows VBScript (`Uruchom_Focus.vbs`) zero-console launcher for instant execution without black cmd flash.\n\n"
            "v0.93 - Zero-Terminal Automated Launchers: added double-clickable `Uruchom_Focus.command` (macOS Gatekeeper auto-clear) and `Uruchom_Focus.bat` (Windows) for instant terminal-free execution after download.\n\n"
            "v0.92 - CI/CD Release Trigger Fix: restored `- 'v*'` pattern under `tags:` in `build-and-release.yml` to trigger automated Release creation upon git tag push.\n\n"
            "v0.91 - Critical Windows Execution Fix: added explicit `scipy` requirement and PyInstaller `--hidden-import=scipy.fftpack` flags to resolve `ModuleNotFoundError: No module named 'scipy'` when initializing audio feature extraction.\n\n"
            "v0.90 - CI/CD GitHub Release Permissions Fix: added explicit `permissions: contents: write` to automated workflow to enable automatic release note generation and ZIP uploading.\n\n"
            "v0.89 - Universal Hardware Acceleration Support: dynamic runtime probing for GPU video encoders across all operating systems.\n"
            "      - Supported GPU engines: NVIDIA NVENC (`h264_nvenc`), Intel Quick Sync (`h264_qsv`), AMD AMF (`h264_amf`), Apple VideoToolbox (`h264_videotoolbox`), and Windows MediaFoundation (`h264_mf`).\n"
            "      - Intelligent fallback to multi-threaded CPU encoding (`libx264` with `-preset veryfast`) on unsupported hardware.\n"
            "      - Automated GitHub Actions workflow (`build-and-release.yml`) for cross-platform binary releases.\n\n"
            "v0.88 - Full cross-platform port for Windows 10/11 & macOS.\n"
            "      - Automated downloading of Windows `.exe` FFmpeg static binaries.\n"
            "      - Cross-platform system paths (`AppData` vs `Library`).\n"
            "      - Implemented OS-specific commands (explorer/startfile vs open).\n"
            "      - Updated build script to auto-generate `.ico` icons for Windows.\n"
            "      - Multi-processing stability patch (`freeze_support`) for Windows builds.\n\n"
            "v0.87 - Prepared repository for open-source GitHub release: sanitized local system paths, generated requirements.txt, .gitignore, and comprehensive README with legal liability disclaimers.\n\n"
            "v0.86 - Fixed FFmpeg sub-sampling rendering errors (black line artifacts) when generating 9:16 crops, fixed language selector positioning bug, updated tutorial instructions, and unified interface color elements.\n\n"
            "v0.85 - Implemented auto-scrolling log window and dynamic percent progress buttons to prevent interface stagnation during long video rendering and face scanning.\n\n"
            "v0.84 - Implemented Target Speaker Voice Fingerprinting: profiles character voice from verified face frames and filters out non-target speakers, narrators, and intros.\n\n"
            "v0.83 - Complete UI/UX overhaul inspired by modern dark web dashboards: added Hero Banner card layout, custom Tkinter animation loops (smooth progress interpolation, hover transitions, pulsing glow button), and preserved dynamic color themes.\n\n"
            "v0.81 - Fixed Interactive Clip Review UI height bug causing the render button to be hidden, and implemented thumbnail extraction via OpenCV to display video frame previews alongside the checklist.\n\n"
            "v0.80 - Implemented 9:16 Vertical Cropping (Auto-Track & Blurred Background), FFmpeg Scene Cut Snapping to align clips with natural shot boundaries, and a two-phase Interactive Clip Review Checklist (Scan -> Review -> Render).\n\n"
            "v0.79 - Implemented AI Voice Activity Detection (VAD) & Active Speaker Alignment to intelligently extend scenes to the nearest silence pause, preventing character speech and sentences from being cut off mid-word.\n\n"
            "v0.78 - Fixed mode switch Auto-Tune synchronization (switching between Anime and Real Faces now automatically triggers Auto-Tune) and fixed macOS sidebar column grid layout to prevent text rendering collapse.\n\n"
            "v0.76 - Deep Code Audit & Refactoring: Fixed OpenCV VideoCapture resource leaks in background scanner, fixed disk space leak (cleared crops), unified cross-thread cascade model paths, and added thread-safe locks.\n\n"
            "v0.75 - Implemented precise audio `atrim` + `apad` for perfect duration matching and `-bf 0` (no B-frames) for zero-freeze sharp scene cuts. Added OpenCV `haarcascade_profileface` fallback for detecting sideways/profile Real Faces.\n\n"
            "v0.74 - Fixed random audio truncation and dropouts by implementing Audio Frame Padding (`apad`), 48kHz audio resampler alignment, and performed a complete codebase stability audit.\n\n"
            "v0.72 - Added Smart Auto-Tune algorithm and dynamic Presets (Anime, Cinematic, Fast Edits) for automatic parameter configuration.\n\n"
            "v0.71 - Fixed audio/video freeze and frame stalls using hard A/V PTS resampling (`-fps_mode cfr`, `min_hard_comp`) and added supported video/image formats list to Tutorial modal.\n\n"
            "v0.70 - Internal stability updates and minor UI refinements.\n\n"
            "v0.67 - Restored missing `import concurrent.futures` in scenepack_generator_gui.py resolving NameError ('concurrent' is not defined) during parallel FFmpeg segment extraction. (haha 67)\n\n"
            "v0.66 - Upgraded Anime face clustering with 1D Hue histogram & 256-bit dHash matching to merge characters across shadows/lighting shifts. Fixed card text formatting and added 1:1 square face thumbnail cropping.\n\n"
            "v0.65 - Added post-scan Face Clustering and Deduplication pass: automatically merges duplicate character captures, selects the best thumbnail, and displays total occurrence counts.\n\n"
            "v0.64 - Fixed macOS Dock app icon rendering using native Cocoa NSApplication icon binding. Enhanced Anime face clustering with center elliptical mask filtering to eliminate duplicate character cards.\n\n"
            "v0.63 - Fixed missing PIL Image import in scenepack_generator_gui.py resolving NameError ('Image' is not defined) in character gallery pre-scanner.\n\n"
            "v0.62 - Upgraded Anime Character Gallery with 2D HSV Color Histogram + Perceptual dHash Feature Clustering. Eliminates multi-card character duplication. Updated Tutorial modal across all languages.\n\n"
            "v0.61 - Implemented multi-encoding secondary merge pass for character deduplication in Beta Gallery (eliminates repeating identical characters). Added hand cursor and localized card labels.\n\n"
            "v0.60 - Fixed Beta character gallery pre-scanner stuck on initialization: added _download_anime_cascade handler to FocusApp and wired missing gallery event queue listeners (gallery_status, gallery_progress, gallery_results, gallery_error).\n\n"
            "v0.59 - Fixed Beta tab mode localization bug preventing face detection in non-English UI languages. Added live execution logging to GUI console and updated Scanner background worker.\n\n"
            "v0.58 - Fixed Beta tab freeze by moving character scanning to a multi-threaded background worker with 2.5s frame stepping and 480p downscaling.\n\n"
            "v0.57 - Introduced Beta Character Gallery: auto-scans video, clusters unique real/anime faces, and allows one-click character selection for scenepack generation. Fixed boundary PTS freeze on 00:00 and file endings.\n\n"
            "v0.56 - Fixed application startup crash by reorganizing variable initialization sequence before UI option menu callbacks.\n\n"
            "v0.55 - Fixed initial 5s stream freeze via accurate seeking buffers (-accurate_seek) and added Minimum Scene Duration filter (1.0s) to eliminate micro-cut glitches.\n\n"
            "v0.54 - Exhaustive Deep Code Audit: Fully dynamic multi-language tooltips for Real Faces/Anime segmented buttons, 100% thread-safe UI queues, and verified pipeline.\n\n"
            "v0.53 - Fixed tooltip text updating and localized color theme name mapping (e.g. `pomarańczowy.json` -> `orange.json`).\n\n"
            "v0.52 - Comprehensive Code Audit & Refactoring: Enforced immutability in settings state, strict input boundary validation (skip >= 1), subprocess file existence checks, and 100% test suite.\n\n"
            "v0.51 - Extracted clean vector camera logo symbol from `ikonka.png` to eliminate background box artifacts on macOS Dock squircle tile.\n\n"
            "v0.50 - Added dynamic macOS squircle Dock & window icon generator matching system appearance mode and color theme.\n\n"
            "v0.49 - Updated application icon source to `ikonka.png` and regenerated native `icon.icns` bundle assets.\n\n"
            "v0.48 - Added native macOS application icon support (`icon.icns`) to build script and window header.\n\n"
            "v0.47 - Eliminated video freezing / audio drift at segment boundaries via closed GOPs (-bf 0), PTS regeneration (-fflags +genpts), and MOOV faststart.\n\n"
            "v0.46 - Optimized application build pipeline: excluded redundant dependencies and enabled binary stripping to drastically reduce bundle size.\n\n"
            "v0.45 - Fixed layout regression by removing duplicate settings frame from main container grid.\n\n"
            "v0.44 - Comprehensive deep code audit & refactoring (cv2.VideoCapture resource leak fixes, interval edge-case clamping, translation fallback keys, and concat file list escaping).\n\n"
            "v0.43 - Added Gap Bridging Tolerance (1.5s) to prevent premature scene cuts during head turns or temporary face occlusions.\n\n"
            "v0.42 - Fixed CTkToplevel window rendering and styling issue on macOS.\n\n"
            "v0.41 - Fixed segmented button selection state loss when switching languages (Real Faces/Anime & Light/Dark/System).\n\n"
            "v0.40 - Full UI i18n translations (Appearance modes, color names, tooltips, placeholders, tutorial & status labels).\n\n"
            "v0.39 - Added multi-language support (Polish, English, German, Russian, Ukrainian, Spanish, French, Japanese) with persistent language settings.\n\n"
            "v0.38 - Enforced permanent system versioning rule (+0.01 per prompt) & fast-seek setpts/asetpts filter pipeline.\n\n"
            "v0.37 - Hybrid fast seeking (-ss before -i) + setpts/asetpts PTS reset filters for high-speed & sync-perfect rendering.\n\n"
            "v0.36 - Expanded granular Changelog tracking all project iterations.\n\n"
            "v0.35 - Centralized APP_VERSION variable across all UI windows and headers.\n\n"
            "v0.34 - Added in-app Changelog window with initial version history.\n\n"
            "v0.33 - Frame-accurate seeking (-ss after -i) to fix ~40s initial clip freezes on raw MKV rips.\n\n"
            "v0.32 - Fast-seeking parameter positioning (-ss) in FFmpeg extraction.\n\n"
            "v0.31 - Multi-threaded parallel segment extraction using ThreadPoolExecutor for 5-10x faster generation.\n\n"
            "v0.30 - Added -start_at_zero flag and verified padding_after clip boundary logic.\n\n"
            "v0.29 - Enforced Constant Frame Rate (CFR -r 24 -fps_mode cfr) & GOP keyframe alignment (-g 24).\n\n"
            "v0.28 - Configured PyInstaller build.py with Focus bundle identifier (com.focus.app).\n\n"
            "v0.27 - Converted How-to-Use guide to read-only CTkTextbox with word wrapping.\n\n"
            "v0.26 - GitHub User-Agent header fix for XML downloads & size validation (>50KB check).\n\n"
            "v0.25 - Added OpenCV cascade.empty() load validation.\n\n"
            "v0.24 - Relocated external binaries and XML to ~/Library/Application Support/Focus for macOS bundle security.\n\n"
            "v0.23 - Tooltip helpers for Real Faces vs Anime modes.\n\n"
            "v0.22 - Added OpenCV Anime face detection mode using lbpcascade_animeface classifier.\n\n"
            "v0.21 - Fixed GUI method scope AttributeError on application startup.\n\n"
            "v0.20 - Added 'How to Use' tutorial Toplevel popup window.\n\n"
            "v0.19 - Audio sync timestamp flags (-avoid_negative_ts make_zero, -fflags +genpts, -async 1).\n\n"
            "v0.18 - Audio/Video duration drift fix using AAC re-encoding (-c:a aac -b:a 192k).\n\n"
            "v0.17 - Official application rebranding to 'Focus'.\n\n"
            "v0.16 - Persistent JSON settings storage (~/.scenepack_generator_settings.json).\n\n"
            "v0.15 - Integrated macOS native completion audio notification (afplay).\n\n"
            "v0.14 - Added custom color theme engine (generate_themes.py).\n\n"
            "v0.13 - Fixed keyframe gray smearing artifacts by removing stream copying (-c copy).\n\n"
            "v0.12 - VideoToolbox Apple Silicon GPU hardware acceleration (-c:v h264_videotoolbox).\n\n"
            "v0.11 - Added stream concat demuxer logic.\n\n"
            "v0.10 - Initial FFmpeg segment extraction logic.\n\n"
            "v0.09 - Face Recognition tolerance adjustment parameter.\n\n"
            "v0.08 - Frame Skip interval speed optimization control.\n\n"
            "v0.07 - Padding Before & Padding After numerical configuration.\n\n"
            "v0.06 - Progress bar and real-time scanning percentage ETA indicator.\n\n"
            "v0.05 - Output save location selector & filename configuration.\n\n"
            "v0.04 - Reference Image picker & preview integration.\n\n"
            "v0.03 - Input Video file picker & path display integration.\n\n"
            "v0.02 - Basic CustomTkinter GUI layout creation.\n\n"
            "v0.01 - Initial CLI prototype for face recognition scenepack cutting."
        )

        textbox = ctk.CTkTextbox(self.changelog_win, wrap="word", font=ctk.CTkFont(size=13), fg_color=("#FFFFFF", "#14161B"))
        textbox.pack(padx=20, pady=10, fill="both", expand=True)
        textbox.insert("1.0", history_text)
        textbox.configure(state="disabled")
        
        btn_close = ctk.CTkButton(self.changelog_win, text=cl_close, command=self.changelog_win.destroy, width=120)
        btn_close.pack(pady=(5, 15))

    def load_settings(self):
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load settings: {e}")
        return {}
        
    def update_dynamic_app_icon(self, theme_color_name: str = None, appearance_mode: str = None):
        """
        Dynamically updates the macOS Dock and Window icon to match system appearance mode
        and selected application color theme.
        """
        try:
            COLOR_MAP = {
                "red": (220, 53, 69),
                "orange": (253, 126, 20),
                "yellow": (255, 193, 7),
                "green": (40, 167, 69),
                "blue": (13, 110, 253),
                "indigo": (102, 16, 242),
                "violet": (111, 66, 193),
                "pink": (214, 51, 132),
            }
            
            if not theme_color_name:
                theme_color_name = self.settings.get("color_theme", "violet")
                
            base_rgb = COLOR_MAP.get(str(theme_color_name).lower(), (111, 66, 193))
            
            if not appearance_mode:
                appearance_mode = self.settings.get("appearance_mode", "Dark")
                
            is_dark = True
            if appearance_mode == "Light":
                is_dark = False
            elif appearance_mode == "System":
                is_dark = ctk.get_appearance_mode() != "Light"

            icon_source = None
            base_paths = [
                Path(__file__).parent,
                Path(getattr(sys, '_MEIPASS', '.')),
                Path.home() / "Library/Application Support/Focus"
            ]
            for b_path in base_paths:
                for icon_name in ["icon.png", "ikonka.png"]:
                    icon_p = b_path / icon_name
                    if icon_p.exists():
                        icon_source = icon_p
                        break
                if icon_source:
                    break
                    
            if not icon_source:
                return

            size = 512
            sq_size = int(size * 0.82)
            offset = (size - sq_size) // 2
            
            mask = Image.new('L', (sq_size, sq_size), 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, sq_size, sq_size), radius=int(sq_size * 0.225), fill=255)
            
            gradient = np.zeros((sq_size, sq_size, 4), dtype=np.uint8)
            factors = 1.0 - (np.arange(sq_size) / float(sq_size)) * 0.28
            for c_idx in range(3):
                gradient[:, :, c_idx] = (base_rgb[c_idx] * factors[:, None]).astype(np.uint8)
            gradient[:, :, 3] = 255
            bg = Image.fromarray(gradient, 'RGBA')
                    
            squircle_tile = Image.new('RGBA', (sq_size, sq_size), (0, 0, 0, 0))
            squircle_tile.paste(bg, (0, 0), mask=mask)
            
            canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            canvas.paste(squircle_tile, (offset, offset), mask=squircle_tile)
            
            # Extract clean white camera logo symbol from icon.png
            sym = Image.open(icon_source).convert('RGBA')
            symbol_mask = sym.convert('L').point(lambda p: 255 if p > 90 else 0)
            
            white_sym = Image.new('RGBA', sym.size, (255, 255, 255, 255))
            white_sym.putalpha(symbol_mask)
            
            sym_size = int(sq_size * 0.58)
            sym_resized = white_sym.resize((sym_size, sym_size), Image.Resampling.LANCZOS)
            
            sym_offset = (size - sym_size) // 2
            canvas.paste(sym_resized, (sym_offset, sym_offset), mask=sym_resized)
            
            self.icon_photo = ImageTk.PhotoImage(canvas)
            self.wm_iconphoto(True, self.icon_photo)

            # Removed Native macOS Dock Icon Binding to allow native icon.icns to be used
        except Exception as e:
            logging.debug(f"Could not update dynamic app icon: {e}")

    def change_appearance_mode_event(self, new_appearance_mode: str):
        mode_map = {
            "Jasny": "Light", "Ciemny": "Dark", "Systemowy": "System",
            "Hell": "Light", "Dunkel": "Dark", "System": "System",
            "Светлая": "Light", "Тёмная": "Dark", "Системная": "System",
            "Світлий": "Light", "Темний": "Dark", "Системний": "System",
            "Claro": "Light", "Oscuro": "Dark", "Sistema": "System",
            "Clair": "Light", "Sombre": "Dark", "Système": "System",
            "ライト": "Light", "ダーク": "Dark", "システム": "System",
            "Light": "Light", "Dark": "Dark"
        }
        actual_mode = mode_map.get(new_appearance_mode, "Dark")
        ctk.set_appearance_mode(actual_mode)
        self.update_dynamic_app_icon(appearance_mode=actual_mode)
        self.save_current_settings()

    def change_theme_event(self, new_theme: str):
        color_map = {
            "red": "red", "orange": "orange", "yellow": "yellow", "green": "green", "blue": "blue", "indigo": "indigo", "violet": "violet", "pink": "pink",
            "czerwony": "red", "pomarańczowy": "orange", "żółty": "yellow", "zielony": "green", "niebieski": "blue", "fioletowy": "violet", "różowy": "pink",
            "rot": "red", "gelb": "yellow", "grün": "green", "blau": "blue", "rosa": "pink",
            "красный": "red", "оранжевый": "orange", "жёлтый": "yellow", "зелёный": "green", "синий": "blue", "индиго": "indigo", "фиолетовый": "violet", "розовый": "pink",
            "червоний": "red", "помаранчевий": "orange", "жовтий": "yellow", "зелений": "green", "синій": "blue", "фіолетовий": "violet", "рожевий": "pink",
            "rojo": "red", "naranja": "orange", "amarillo": "yellow", "verde": "green", "azul": "blue", "púrpura": "violet", "rosa": "pink",
            "rouge": "red", "jaune": "yellow", "vert": "green", "bleu": "blue", "violet": "violet", "rose": "pink",
            "赤": "red", "オレンジ": "orange", "黄色": "yellow", "緑": "green", "青": "blue", "インディゴ": "indigo", "紫": "violet", "ピンク": "pink"
        }
        actual_theme = color_map.get(new_theme.lower(), new_theme.lower())
        self._apply_theme(actual_theme)
        self.update_dynamic_app_icon(theme_color_name=actual_theme)
        self.save_current_settings()
    def _apply_theme(self, theme_name: str):
        # Resolve localized theme strings to canonical English filenames
        canonical_colors = ["red", "orange", "yellow", "green", "blue", "indigo", "violet", "pink"]
        for lang_dict in TRANSLATIONS.values():
            if "colors" in lang_dict and theme_name in lang_dict["colors"]:
                idx = lang_dict["colors"].index(theme_name)
                theme_name = canonical_colors[idx]
                break

        if theme_name in ["blue", "green", "dark-blue"]:
            ctk.set_default_color_theme(theme_name)
        else:
            if hasattr(sys, '_MEIPASS'):
                base_dir = Path(sys._MEIPASS)
            else:
                base_dir = Path(__file__).parent
            theme_path = base_dir / "themes" / f"{theme_name}.json"
            if theme_path.exists():
                ctk.set_default_color_theme(str(theme_path))
            else:
                logging.error(f"Theme file not found: {theme_path}")
                ctk.set_default_color_theme("blue")
                theme_name = "blue"

        # Dynamically update existing UI widgets to reflect new color theme without requiring app restart
        self.update_ui_theme_colors(theme_name)

    def update_ui_theme_colors(self, theme_name: str):
        if not hasattr(self, 'btn_sel_video'):
            return
        hex_color = THEME_COLORS.get(theme_name, "#3498DB")
        hover_hex = THEME_HOVER_COLORS.get(theme_name, "#2874A6")
        
        # Update buttons
        for btn_name in ['btn_sel_video', 'btn_sel_ref', 'btn_sel_output', 'btn_auto_tune', 'btn_scan_gallery']:
            btn = getattr(self, btn_name, None)
            if btn:
                try:
                    btn.configure(fg_color=hex_color, hover_color=hover_hex)
                except Exception:
                    pass
                
        if hasattr(self, 'btn_generate') and self.btn_generate:
            try:
                self.btn_generate.configure(fg_color=hex_color, hover_color=hover_hex, border_color=hex_color)
            except Exception:
                pass
            
        if hasattr(self, 'hero_banner') and self.hero_banner:
            try:
                self.hero_banner.configure(border_color=hex_color)
            except Exception:
                pass
            
        # Update progress bars
        for pbar_name in ['progress_bar', 'gallery_progress_bar']:
            pbar = getattr(self, pbar_name, None)
            if pbar:
                try:
                    pbar.configure(progress_color=hex_color)
                except Exception:
                    pass
                
        # Update sliders and switches
        if hasattr(self, 'slider_vad_speaker_threshold') and self.slider_vad_speaker_threshold:
            try:
                self.slider_vad_speaker_threshold.configure(button_color=hex_color, button_hover_color=hover_hex, progress_color=hex_color)
            except Exception:
                pass
            
        if hasattr(self, 'sound_switch') and self.sound_switch:
            try:
                self.sound_switch.configure(progress_color=hex_color, button_color=hex_color, button_hover_color=hover_hex)
            except Exception:
                pass
            
        # Update segmented buttons
        for seg_name in ['mode_switch', 'tab_switcher', 'appearance_mode_optionemenu']:
            seg = getattr(self, seg_name, None)
            if seg:
                try:
                    seg.configure(selected_color=hex_color, selected_hover_color=hover_hex)
                except Exception:
                    pass

    def change_language_event(self, selected_language: str):
        self.settings["language"] = selected_language
        self._apply_language(selected_language)
        self.save_current_settings()

    def _apply_language(self, lang_name: str):
        self.appearance_mode_label.configure(text=get_translation(lang_name, "appearance"))
        self.color_theme_label.configure(text=get_translation(lang_name, "theme"))
        self.language_label.configure(text=get_translation(lang_name, "language"))
        self.sound_switch.configure(text=get_translation(lang_name, "play_sound"))
        self.btn_tutorial.configure(text=get_translation(lang_name, "how_to_use"))
        self.btn_changelog.configure(text=get_translation(lang_name, "changelog"))
        self.dashboard_label.configure(text=get_translation(lang_name, "dashboard"))
        self.btn_sel_video.configure(text=get_translation(lang_name, "sel_video"))
        self.btn_sel_ref.configure(text=get_translation(lang_name, "sel_ref"))
        self.btn_sel_output.configure(text=get_translation(lang_name, "sel_output"))
        self.lbl_pad_before.configure(text=get_translation(lang_name, "pad_before"))
        self.lbl_pad_after.configure(text=get_translation(lang_name, "pad_after"))
        self.lbl_max_gap.configure(text=get_translation(lang_name, "max_gap"))
        self.lbl_min_scene.configure(text=get_translation(lang_name, "min_scene"))
        self.lbl_frame_skip.configure(text=get_translation(lang_name, "frame_skip"))
        self.cb_vad_enabled.configure(text=get_translation(lang_name, "vad_enable"))
        self.lbl_vad_buffer.configure(text=get_translation(lang_name, "vad_buffer"))
        self.cb_vad_speaker_enabled.configure(text=get_translation(lang_name, "vad_speaker_enable"))
        self.lbl_vad_speaker_threshold.configure(text=get_translation(lang_name, "vad_speaker_threshold"))
        self.btn_generate.configure(text=get_translation(lang_name, "generate"))
        self.lbl_review.configure(text=get_translation(lang_name, "review"))
        self.btn_play_orig.configure(text=get_translation(lang_name, "play_orig"))
        self.btn_play_scene.configure(text=get_translation(lang_name, "play_result"))
        
        # Placeholders
        if self.video_path_var.get() in [v.get("no_video", "") for v in TRANSLATIONS.values()]:
            self.video_path_var.set(get_translation(lang_name, "no_video"))
        if self.image_path_var.get() in [v.get("no_image", "") for v in TRANSLATIONS.values()]:
            self.image_path_var.set(get_translation(lang_name, "no_image"))
        if self.output_path_var.get() in [v.get("no_output", "") for v in TRANSLATIONS.values()]:
            self.output_path_var.set(get_translation(lang_name, "no_output"))
            
        # Status Label
        if self.eta_label.cget("text") in [v.get("ready", "") for v in TRANSLATIONS.values()]:
            self.eta_label.configure(text=get_translation(lang_name, "ready"))
            
        # Segmented Buttons Options - Preserve Active Selection Index!
        curr_app_val = self.appearance_mode_optionemenu.get()
        app_idx = 1 # Default Dark
        for l_dict in TRANSLATIONS.values():
            if curr_app_val == l_dict.get("light"):
                app_idx = 0
                break
            elif curr_app_val == l_dict.get("dark"):
                app_idx = 1
                break
            elif curr_app_val == l_dict.get("system"):
                app_idx = 2
                break

        new_app_values = [get_translation(lang_name, "light"), get_translation(lang_name, "dark"), get_translation(lang_name, "system")]
        self.appearance_mode_optionemenu.configure(values=new_app_values)
        self.appearance_mode_optionemenu.set(new_app_values[app_idx])

        curr_face_val = self.mode_switch.get()
        face_idx = 0 # Default Real Faces
        for l_dict in TRANSLATIONS.values():
            if curr_face_val == l_dict.get("real_faces"):
                face_idx = 0
                break
            elif curr_face_val == l_dict.get("anime"):
                face_idx = 1
                break

        new_face_values = [get_translation(lang_name, "real_faces"), get_translation(lang_name, "anime")]
        self.mode_switch.configure(values=new_face_values)
        self.mode_switch.set(new_face_values[face_idx])
        self.mode_var.set(new_face_values[face_idx])
        
        # Color Theme Menu Options - Preserve Active Selection Index!
        curr_color_val = self.color_theme_optionmenu.get()
        color_idx = 4 # Default blue
        for l_dict in TRANSLATIONS.values():
            if "colors" in l_dict and curr_color_val in l_dict["colors"]:
                color_idx = l_dict["colors"].index(curr_color_val)
                break
        
        new_color_values = TRANSLATIONS.get(lang_name, TRANSLATIONS["English"]).get("colors", TRANSLATIONS["English"]["colors"])
        self.color_theme_optionmenu.configure(values=new_color_values)
        self.color_theme_optionmenu.set(new_color_values[color_idx])
        
        # Tooltips
        if hasattr(self, 'tt_pad_before'):
            self.tt_pad_before.set_text(get_translation(lang_name, "tt_pad_before"))
            self.tt_pad_before_entry.set_text(get_translation(lang_name, "tt_pad_before"))
            self.tt_pad_after.set_text(get_translation(lang_name, "tt_pad_after"))
            self.tt_pad_after_entry.set_text(get_translation(lang_name, "tt_pad_after"))
            self.tt_max_gap.set_text(get_translation(lang_name, "tt_max_gap"))
            self.tt_max_gap_entry.set_text(get_translation(lang_name, "tt_max_gap"))
            self.tt_min_scene.set_text(get_translation(lang_name, "tt_min_scene"))
            self.tt_min_scene_entry.set_text(get_translation(lang_name, "tt_min_scene"))
            self.tt_frame_skip.set_text(get_translation(lang_name, "tt_frame_skip"))
            self.tt_frame_skip_entry.set_text(get_translation(lang_name, "tt_frame_skip"))
            
        self._add_mode_tooltips()

    def save_current_settings(self, *_):
        # Immutability principle: Create a new dictionary object rather than mutating in-place
        new_settings = dict(self.settings)

        curr_app_val = self.appearance_mode_optionemenu.get()
        app_modes_canonical = ["Light", "Dark", "System"]
        app_idx = 1
        for lang_dict in TRANSLATIONS.values():
            if curr_app_val == lang_dict["light"]:
                app_idx = 0
                break
            elif curr_app_val == lang_dict["dark"]:
                app_idx = 1
                break
            elif curr_app_val == lang_dict["system"]:
                app_idx = 2
                break
        new_settings["appearance_mode"] = app_modes_canonical[app_idx]

        curr_color_val = self.color_theme_optionmenu.get()
        canonical_colors = ["red", "orange", "yellow", "green", "blue", "indigo", "violet", "pink"]
        color_idx = 4
        for lang_dict in TRANSLATIONS.values():
            if curr_color_val in lang_dict["colors"]:
                color_idx = lang_dict["colors"].index(curr_color_val)
                break
        new_settings["color_theme"] = canonical_colors[color_idx]
        new_settings["language"] = self.language_optionmenu.get()
        new_settings["frame_skip"] = max(1, int(self.frame_skip_var.get()))
        new_settings["vad_enabled"] = self.vad_enabled_var.get()
        new_settings["vad_buffer"] = max(50, int(self.vad_buffer_var.get()))
        new_settings["vad_speaker_enabled"] = self.vad_speaker_enabled_var.get()
        new_settings["vad_speaker_threshold"] = self.vad_speaker_threshold_var.get()
        new_settings["play_sound"] = self.play_sound_var.get()
        try:
            new_settings["pad_before"] = max(0.0, float(self.pad_before_var.get()))
            new_settings["pad_after"] = max(0.0, float(self.pad_after_var.get()))
            new_settings["max_gap_tolerance"] = max(0.0, float(self.max_gap_var.get()))
            new_settings["min_scene_duration"] = max(0.0, float(self.min_scene_var.get()))
            new_settings["frame_skip"] = max(1, int(self.frame_skip_var.get()))
        except ValueError:
            pass # Ignore saving invalid entry box values
            
        self.settings = new_settings
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save settings: {e}")

    def _on_mode_switched(self, selected_mode: str = None):
        """Callback when user toggles mode switch (Real Faces <-> Anime). Re-runs Auto-Tune with new mode."""
        self.apply_auto_tune()

    def _switch_main_view(self, selected_tab: str):
        if selected_tab in ["Generator", get_translation(self.settings.get("language", "English"), "generator_tab")]:
            self.gallery_view.pack_forget()
            self.generator_view.pack(fill="both", expand=True)
        else:
            self.generator_view.pack_forget()
            self.gallery_view.pack(fill="both", expand=True)
        self.update_ui_theme_colors(self.settings.get("color_theme", "blue"))

    def _download_anime_cascade(self):
        if not hasattr(self, 'anime_cascade_path'):
            self.app_dir = Path(os.path.expanduser('~/Library/Application Support/Focus'))
            self.app_dir.mkdir(parents=True, exist_ok=True)
            self.anime_cascade_path = self.app_dir / "lbpcascade_animeface.xml"

        with CASCADE_DOWNLOAD_LOCK:
            if not self.anime_cascade_path.exists() or self.anime_cascade_path.stat().st_size < 50000:
                self.log_queue.put(("log", "Downloading anime face cascade model..."))
                url = "https://raw.githubusercontent.com/nagadomi/lbpcascade_animeface/master/lbpcascade_animeface.xml"
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response, open(self.anime_cascade_path, 'wb') as out_file:
                        shutil.copyfileobj(response, out_file)
                        
                    if self.anime_cascade_path.stat().st_size < 50000:
                        if self.anime_cascade_path.exists():
                            self.anime_cascade_path.unlink()
                        raise RuntimeError("Downloaded file size is under 50KB; download was likely blocked or corrupted.")
                        
                    self.log_queue.put(("log", "Successfully downloaded anime face cascade model."))
                except Exception as e:
                    if self.anime_cascade_path.exists():
                        self.anime_cascade_path.unlink()
                    self.log_queue.put(("log", f"Failed to download anime cascade model: {e}"))
                    raise RuntimeError(f"Failed to download anime cascade model: {e}")

    def start_gallery_scan(self):
        v_path = self.video_path_var.get()
        if not v_path or v_path == "No video selected" or not os.path.isfile(v_path):
            messagebox.showwarning("No Input Video", "Please select a valid input video file before scanning for characters.")
            return

        self._cancel_gallery_scan = False
        self.btn_scan_gallery.configure(state="disabled")
        self.btn_cancel_gallery.configure(state="normal")
        self.gallery_progress_bar.set(0)
        self.lbl_gallery_status.configure(text="Initializing background pre-scanner...", text_color="gray60")
        
        mode = self.mode_var.get()
        thread = threading.Thread(target=self._async_scan_video, args=(v_path, mode), daemon=True)
        thread.start()

    def cancel_gallery_scan(self):
        self._cancel_gallery_scan = True
        self.lbl_gallery_status.configure(text="Cancelling scan...", text_color="orange")
        self.btn_cancel_gallery.configure(state="disabled")

    def _async_scan_video(self, video_path_str: str, mode_raw: str):
        """Asynchronously scans raw video in a background worker thread using fast 2.5s frame seeking & 480p downscaling."""
        mode = canonicalize_mode(mode_raw)
        try:
            video_path = Path(video_path_str)
            if not video_path.is_file():
                err_msg = f"Video file not found: {video_path_str}"
                logging.error(err_msg)
                self.log_queue.put(("log", err_msg))
                self.log_queue.put(("gallery_error", err_msg))
                return

            msg_start = f"Starting background character pre-scan in '{mode}' mode (from '{mode_raw}') on '{video_path.name}'..."
            logging.info(msg_start)
            self.log_queue.put(("log", msg_start))
            self.log_queue.put(("gallery_status", msg_start))

            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                err_msg = f"Could not open video file: {video_path.name}"
                logging.error(err_msg)
                self.log_queue.put(("log", err_msg))
                self.log_queue.put(("gallery_error", err_msg))
                return

            try:
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if fps <= 0: fps = 24.0
                if total_frames <= 0: total_frames = 1000
                
                # Fast frame stepping: analyze 1 frame every 2.5 seconds
                sample_step = max(1, int(fps * 2.5))
                
                curr_frame = 0
                sampled_count = 0
                raw_candidates = []
                
                cascade = None
                profile_cascade = None
                if mode == "Anime":
                    self.log_queue.put(("log", "Downloading/preparing anime face cascade classifier..."))
                    self._download_anime_cascade()
                    cascade = cv2.CascadeClassifier(str(self.anime_cascade_path))
                    if cascade.empty():
                        err_msg = "Failed to load anime cascade classifier XML model."
                        logging.error(err_msg)
                        self.log_queue.put(("log", err_msg))
                        self.log_queue.put(("gallery_error", err_msg))
                        return
                elif mode == "Real Faces":
                    profile_cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_profileface.xml')
                    profile_cascade = cv2.CascadeClassifier(profile_cascade_path)
    
                crops_dir = Path(tempfile.gettempdir()) / "focus_gallery_crops"
                if crops_dir.exists():
                    shutil.rmtree(crops_dir, ignore_errors=True)
                crops_dir.mkdir(parents=True, exist_ok=True)
    
                while curr_frame < total_frames and not self._cancel_gallery_scan:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, curr_frame)
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    sampled_count += 1
                    prog = min(1.0, curr_frame / float(total_frames))
                    status_text = f"Scanning... {int(prog * 100)}% (Sampled {sampled_count} frames, Found {len(raw_candidates)} face candidate(s))"
                    self.log_queue.put(("gallery_progress", prog, status_text))
    
                    if sampled_count % 15 == 0 or sampled_count == 1:
                        logging.info(status_text)
                        self.log_queue.put(("log", status_text))
    
                    h, w = frame.shape[:2]
                    if w > 480:
                        ratio = 480.0 / w
                        new_h = int(h * ratio)
                        small_frame = cv2.resize(frame, (480, new_h))
                    else:
                        small_frame = frame
                        
                    if mode == "Real Faces":
                        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                        face_locations = face_recognition.face_locations(rgb_frame, model="hog")
                        
                        if not face_locations and profile_cascade and not profile_cascade.empty():
                            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                            
                            profiles_right = profile_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                            for (x, y, w, h) in profiles_right:
                                face_locations.append((y, x+w, y+h, x))
                                
                            flipped_gray = cv2.flip(gray, 1)
                            profiles_left = profile_cascade.detectMultiScale(flipped_gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                            h_img, w_img = gray.shape
                            for (x, y, w, h) in profiles_left:
                                x_real = w_img - (x + w)
                                face_locations.append((y, x_real+w, y+h, x_real))
    
                        if face_locations:
                            encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                            for loc, encoding in zip(face_locations, encodings):
                                top, right, bottom, left = loc
                                face_crop_rgb = make_square_crop(rgb_frame, top, right, bottom, left, pad_ratio=0.30)
                                if face_crop_rgb is None or face_crop_rgb.size == 0:
                                    continue
                                    
                                pil_crop = Image.fromarray(face_crop_rgb)
                                crop_path = crops_dir / f"char_cand_{sampled_count}_{len(raw_candidates)}.png"
                                pil_crop.save(crop_path)
                                
                                raw_candidates.append({
                                    'crop_path': str(crop_path),
                                    'pil_image': pil_crop,
                                    'resolution': pil_crop.width * pil_crop.height,
                                    'encoding': encoding,
                                    'anime_feature': None
                                })
    
                    elif mode == "Anime" and cascade is not None:
                        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                        for (x, y, fw, fh) in faces:
                            crop_bgr = make_square_crop(small_frame, y, x + fw, y + fh, x, pad_ratio=0.30)
                            if crop_bgr is None or crop_bgr.size == 0:
                                continue
                                
                            crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
                            pil_crop = Image.fromarray(crop_rgb)
                            crop_path = crops_dir / f"anime_cand_{sampled_count}_{len(raw_candidates)}.png"
                            pil_crop.save(crop_path)
                            
                            feat = extract_anime_face_features(crop_bgr)
                            raw_candidates.append({
                                'crop_path': str(crop_path),
                                'pil_image': pil_crop,
                                'resolution': pil_crop.width * pil_crop.height,
                                'encoding': None,
                                'anime_feature': feat
                            })
    
                    curr_frame += sample_step
            finally:
                cap.release()
            
            # POST-SCAN CLUSTERING & DEDUPLICATION LOGIC
            self.log_queue.put(("log", f"Running post-scan face clustering pass over {len(raw_candidates)} candidate face(s)..."))
            merged_clusters = []
            for candidate in raw_candidates:
                matched_merged = None
                if mode == "Real Faces" and candidate['encoding'] is not None:
                    for mc in merged_clusters:
                        dists = face_recognition.face_distance(mc['encodings'], candidate['encoding'])
                        if len(dists) > 0 and min(dists) <= 0.55:
                            matched_merged = mc
                            break
                elif mode == "Anime" and candidate['anime_feature'] is not None:
                    for mc in merged_clusters:
                        for ref_feat in mc['anime_features']:
                            if is_anime_feature_match(candidate['anime_feature'], ref_feat):
                                matched_merged = mc
                                break
                        if matched_merged:
                            break

                if matched_merged:
                    matched_merged['count'] += 1
                    matched_merged['crops'].append(candidate)
                    if mode == "Real Faces" and candidate['encoding'] is not None:
                        matched_merged['encodings'].append(candidate['encoding'])
                    elif mode == "Anime" and candidate['anime_feature'] is not None:
                        matched_merged['anime_features'].append(candidate['anime_feature'])
                else:
                    new_cluster = {
                        'id': len(merged_clusters) + 1,
                        'count': 1,
                        'crops': [candidate],
                        'encodings': [candidate['encoding']] if candidate['encoding'] is not None else [],
                        'anime_features': [candidate['anime_feature']] if candidate['anime_feature'] is not None else []
                    }
                    merged_clusters.append(new_cluster)

            # Select SINGLE highest-quality crop (largest resolution) for each merged cluster
            for mc in merged_clusters:
                best_crop = max(mc['crops'], key=lambda item: item['resolution'])
                mc['crop_path'] = best_crop['crop_path']
                mc['pil_image'] = best_crop['pil_image']

            # Sort gallery cards by occurrence count (most frequent screen-time characters appear first)
            merged_clusters.sort(key=lambda x: x['count'], reverse=True)

            # Re-index cluster IDs post-sort so #1 is the top occurrence character
            for idx, mc in enumerate(merged_clusters, 1):
                mc['id'] = idx

            if self._cancel_gallery_scan:
                msg_cancel = f"Gallery pre-scan cancelled. Discovered {len(merged_clusters)} unique character profile(s)."
                logging.info(msg_cancel)
                self.log_queue.put(("log", msg_cancel))
                self.log_queue.put(("gallery_cancelled", merged_clusters))
            else:
                msg_done = f"Gallery pre-scan complete! Consolidated {len(raw_candidates)} detection(s) into {len(merged_clusters)} unique character profile(s)."
                logging.info(msg_done)
                self.log_queue.put(("log", msg_done))
                self.log_queue.put(("gallery_results", merged_clusters))
            
        except Exception as e:
            err_msg = f"Gallery scan failed: {e}"
            logging.error(err_msg)
            self.log_queue.put(("log", err_msg))
            self.log_queue.put(("gallery_error", err_msg))

    def _display_gallery_cards(self, clusters):
        for widget in self.gallery_scroll_frame.winfo_children():
            widget.destroy()
            
        self._gallery_card_frames = []

        if not clusters:
            lbl = ctk.CTkLabel(self.gallery_scroll_frame, text="No character pre-scan performed yet or no faces discovered.\nClick 'Scan Video for Characters' above!", font=ctk.CTkFont(size=14), text_color="gray60")
            lbl.pack(pady=50)
            return

        for c in range(4):
            self.gallery_scroll_frame.grid_columnconfigure(c, weight=1)

        lang = self.settings.get("language", "English")
        char_title_prefix = get_translation(lang, "char_label")
        det_suffix = get_translation(lang, "detections_label")

        for idx, cluster in enumerate(clusters):
            r = idx // 4
            c = idx % 4

            card = ctk.CTkFrame(self.gallery_scroll_frame, corner_radius=12, fg_color=("gray85", "gray20"), border_width=0, border_color="#215d9c", cursor="hand2")
            card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")

            pil_crop = cluster['pil_image']
            ctk_img = ctk.CTkImage(light_image=pil_crop, dark_image=pil_crop, size=(110, 110))
            
            lbl_img = ctk.CTkLabel(card, image=ctk_img, text="", cursor="hand2")
            lbl_img.pack(padx=10, pady=(10, 5))

            lbl_title = ctk.CTkLabel(card, text=f"{char_title_prefix} #{cluster['id']}", font=ctk.CTkFont(weight="bold"), cursor="hand2")
            lbl_title.pack(padx=5, pady=(2, 0))

            badge_fmt = get_translation(lang, "detections_badge")
            if "{count}" in badge_fmt:
                badge_text = badge_fmt.format(count=cluster['count'])
            else:
                badge_text = f"{cluster['count']} {det_suffix}"

            lbl_count = ctk.CTkLabel(card, text=badge_text, font=ctk.CTkFont(size=11, weight="bold"), text_color="#3b82f6", cursor="hand2")
            lbl_count.pack(padx=5, pady=(0, 10))

            def make_handler(cl=cluster, cd=card):
                return lambda event=None: self._select_gallery_character(cl, cd)

            handler = make_handler()
            card.bind("<Button-1>", handler)
            lbl_img.bind("<Button-1>", handler)
            lbl_title.bind("<Button-1>", handler)
            lbl_count.bind("<Button-1>", handler)

            self._gallery_card_frames.append(card)

    def _select_gallery_character(self, cluster, card_frame):
        self.image_path_var.set(cluster['crop_path'])
        self.save_current_settings()
        
        for cd in self._gallery_card_frames:
            cd.configure(border_width=0)
            
        card_frame.configure(border_width=3, border_color=("#007AFF", "#215d9c"))
        
        msg = f"Selected Character #{cluster['id']} as target reference face for Scenepack generation!"
        logging.info(msg)
        self.lbl_gallery_status.configure(text=msg, text_color="#3b82f6")

    def _animate_progress_bar(self, target_val: float):
        """Sets the target progress for the background animation loop."""
        self._target_progress = target_val

    def _animate_reveal(self, target_height: int = 60, current_height: int = 0):
        """Smoothly expands the review frame height."""
        if current_height == 0:
            self.frame_review.configure(height=0)
            self.frame_review.pack(fill="x", pady=(0, 20), before=self.log_textbox)
            
        if current_height < target_height:
            new_height = min(current_height + max(2, (target_height - current_height) // 3), target_height)
            self.frame_review.configure(height=new_height)
            self.after(15, self._animate_reveal, target_height, new_height)
        else:
            self.frame_review.pack_propagate(True) # let it behave normally after reveal

    def check_log_queue(self):
        """Thread-safe queue reader scheduled on the main GUI loop."""
        while not self.log_queue.empty():
            msg_type, *content = self.log_queue.get()
            if msg_type == "log":
                msg = content[0]
                self.log_textbox.configure(state="normal")
                self.log_textbox.insert("end", msg + "\n")
                self.log_textbox.see("end")
                self.log_textbox.configure(state="disabled")
                
                if hasattr(self, "generator_view") and hasattr(self.generator_view, "_parent_canvas"):
                    self.generator_view._parent_canvas.yview_moveto(1.0)
                    
            elif msg_type == "error":
                msg = content[0]
                messagebox.showerror("Execution Error", msg)
            elif msg_type == "progress":
                val, text = content
                self._animate_progress_bar(val)
                self.eta_label.configure(text=text)
                if getattr(self, "_is_scanning", False):
                    self.btn_generate.configure(text=f"Scanning & Analyzing... {int(val*100)}%")
                elif getattr(self, "_is_rendering", False):
                    self.btn_render.configure(text=f"Rendering... {int(val*100)}%")
            elif msg_type == "reset_btn":
                self.btn_generate.configure(state="normal", text="✓ Finished! (Scan Again)")
                self._is_scanning = False
            elif msg_type == "reset_render_btn":
                self.btn_render.configure(state="normal", text="✓ Render Complete!")
                self._is_rendering = False
            elif msg_type == "show_review_checklist":
                intervals, thumbnails = content[0]
                self.review_checkboxes = []
                # Important: keep image references so they are not garbage collected
                self._review_images = []
                for i, interval in enumerate(intervals):
                    start, end, avg_x = interval
                    duration = end - start
                    var = ctk.BooleanVar(value=True)
                    text = f"Clip {i+1}: {start:.2f}s - {end:.2f}s (Duration: {duration:.2f}s)"
                    
                    row_frame = ctk.CTkFrame(self.review_scroll_frame, fg_color="transparent")
                    row_frame.pack(fill="x", pady=5, padx=10)
                    
                    cb = ctk.CTkCheckBox(row_frame, text=text, variable=var, font=ctk.CTkFont(size=14, weight="bold"))
                    cb.pack(side="left", padx=10)
                    
                    if thumbnails and i < len(thumbnails) and thumbnails[i] is not None:
                        # Ensure we convert PIL image to CTkImage safely inside the main thread
                        ctk_img = ctk.CTkImage(light_image=thumbnails[i], dark_image=thumbnails[i], size=thumbnails[i].size)
                        self._review_images.append(ctk_img)
                        lbl_img = ctk.CTkLabel(row_frame, image=ctk_img, text="")
                        lbl_img.pack(side="right", padx=10)
                    
                    self.review_checkboxes.append((interval, var))
                self._animate_reveal(target_height=350)
                if self.play_sound_var.get():
                    try:
                        if platform.system() == "Darwin":
                            subprocess.Popen(['afplay', '/System/Library/Sounds/Glass.aiff'])
                        elif platform.system() == "Windows":
                            import winsound
                            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                    except Exception as e:
                        logging.error(f"Failed to play notification sound: {e}")
            elif msg_type == "gallery_status":
                text = content[0]
                self.lbl_gallery_status.configure(text=text, text_color="gray60")
            elif msg_type == "gallery_progress":
                val, text = content
                self.gallery_progress_bar.set(val)
                self.lbl_gallery_status.configure(text=text, text_color="gray60")
            elif msg_type == "gallery_results":
                clusters = content[0]
                self.btn_scan_gallery.configure(state="normal")
                self.btn_cancel_gallery.configure(state="disabled")
                self.gallery_progress_bar.set(1.0)
                self.lbl_gallery_status.configure(text=f"Scan complete! Discovered {len(clusters)} unique character cluster(s).", text_color="#22c55e")
                self._display_gallery_cards(clusters)
            elif msg_type == "gallery_cancelled":
                clusters = content[0]
                self.btn_scan_gallery.configure(state="normal")
                self.btn_cancel_gallery.configure(state="disabled")
                self.lbl_gallery_status.configure(text=f"Scan cancelled. Discovered {len(clusters)} character cluster(s).", text_color="orange")
                self._display_gallery_cards(clusters)
            elif msg_type == "gallery_error":
                err_msg = content[0]
                self.btn_scan_gallery.configure(state="normal")
                self.btn_cancel_gallery.configure(state="disabled")
                self.lbl_gallery_status.configure(text=err_msg, text_color="red")
                
        self.after(100, self.check_log_queue)

    def play_original(self):
        v_path = self.video_path_var.get()
        if v_path and os.path.isfile(v_path):
            try:
                if platform.system() == "Windows":
                    os.startfile(v_path)
                else:
                    subprocess.Popen(['open', v_path])
            except Exception as e:
                logging.error(f"Failed to open original video: {e}")

    def play_scenepack(self):
        o_path = self.output_path_var.get()
        if o_path and os.path.isfile(o_path):
            try:
                if platform.system() == "Windows":
                    os.startfile(o_path)
                else:
                    subprocess.Popen(['open', o_path])
            except Exception as e:
                logging.error(f"Failed to open generated scenepack: {e}")

    def apply_auto_tune(self):
        """Dynamically analyzes video metadata (FPS, mode Anime vs Real Faces) and sets optimal parameter defaults."""
        mode = canonicalize_mode(self.mode_var.get())
        video_path_str = self.video_path_var.get()
        
        video_fps = 24.0
        if video_path_str and os.path.isfile(video_path_str):
            try:
                cap = cv2.VideoCapture(video_path_str)
                if cap.isOpened():
                    fps_val = cap.get(cv2.CAP_PROP_FPS)
                    if fps_val > 0:
                        video_fps = fps_val
                    cap.release()
            except Exception as ex:
                logging.debug(f"Auto-tune video FPS read note: {ex}")

        if mode == "Anime":
            frame_skip = max(6, int(video_fps / 3.0))
            max_gap = 1.8
            pad_before = 0.8
            pad_after = 0.8
            min_scene = 0.8
        else:
            frame_skip = max(12, int(video_fps / 2.0))
            max_gap = 1.5
            pad_before = 1.5
            pad_after = 1.5
            min_scene = 1.2

        self.pad_before_var.set(str(pad_before))
        self.pad_after_var.set(str(pad_after))
        self.max_gap_var.set(str(max_gap))
        self.min_scene_var.set(str(min_scene))
        self.frame_skip_var.set(str(frame_skip))
        self.save_current_settings()

        msg = f"✨ Auto-Tune applied for '{mode}' mode ({video_fps:.1f} FPS)!"
        logging.info(msg)
        self.eta_label.configure(text=msg, text_color=("#5856D6", "#8b5cf6"))

    def _on_preset_selected(self, selected_preset: str):
        """Applies parameter configuration for the selected preset profile."""
        preset_str = str(selected_preset).lower()
        if "auto-tune" in preset_str or "zalecan" in preset_str:
            self.apply_auto_tune()
            return
            
        if "fast" in preset_str or "szybki" in preset_str or "tiktok" in preset_str:
            pad_before, pad_after, max_gap, min_scene, frame_skip = 0.4, 0.4, 0.8, 0.5, 8
        elif "cinematic" in preset_str or "kinow" in preset_str or "długie" in preset_str:
            pad_before, pad_after, max_gap, min_scene, frame_skip = 2.0, 2.0, 2.5, 2.0, 15
        elif "draft" in preset_str or "szkic" in preset_str:
            pad_before, pad_after, max_gap, min_scene, frame_skip = 1.0, 1.0, 1.5, 1.0, 24
        else:
            self.apply_auto_tune()
            return

        self.pad_before_var.set(str(pad_before))
        self.pad_after_var.set(str(pad_after))
        self.max_gap_var.set(str(max_gap))
        self.min_scene_var.set(str(min_scene))
        self.frame_skip_var.set(str(frame_skip))
        self.save_current_settings()

        msg = f"Applied Preset Profile: {selected_preset}"
        logging.info(msg)
        self.eta_label.configure(text=msg, text_color="#3b82f6")

    def select_video(self):
        path = filedialog.askopenfilename(title="Select Input Video", filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi *.webm *.flv *.m4v *.ts *.wmv"), ("All Files", "*.*")])
        if path:
            self.video_path_var.set(path)
            self.apply_auto_tune()

    def select_image(self):
        path = filedialog.askopenfilename(title="Select Reference Image", filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff"), ("All Files", "*.*")])
        if path:
            self.image_path_var.set(path)
            
    def select_output(self):
        path = filedialog.asksaveasfilename(title="Save Output As", defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4"), ("All Files", "*.*")])
        if path:
            self.output_path_var.set(path)

    def start_scan(self):
        v_path = self.video_path_var.get()
        i_path = self.image_path_var.get()
        o_path = self.output_path_var.get()
        mode = self.mode_var.get()
        
        if not v_path or not i_path or not o_path:
            messagebox.showerror("Missing Files", "Please select the input video, reference image, and output location.")
            return
            
        try:
            pad_before = max(0.0, float(self.pad_before_var.get()))
            pad_after = max(0.0, float(self.pad_after_var.get()))
            max_gap = max(0.0, float(self.max_gap_var.get()))
            min_scene = max(0.0, float(self.min_scene_var.get()))
            skip = max(1, int(self.frame_skip_var.get()))
            vad_enabled = self.vad_enabled_var.get()
            vad_buffer = max(50, int(self.vad_buffer_var.get()))
            vad_speaker_enabled = self.vad_speaker_enabled_var.get()
            vad_speaker_threshold = self.vad_speaker_threshold_var.get()
        except ValueError:
            messagebox.showerror("Invalid Input", "Padding, gap tolerance, scene length, and frame skip must be numeric values.")
            return

        # Disable button and update text
        self._is_scanning = True
        self.btn_generate.configure(state="disabled", text="Scanning & Analyzing... (Check Logs)")
        self._target_progress = 0.0
        self.progress_bar.set(0)
        self.eta_label.configure(text="Initializing scan...")
        
        # Hide review frame if visible
        for widget in self.review_scroll_frame.winfo_children():
            widget.destroy()
        
        # Clear previous logs
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        
        # Spawn background thread to prevent UI freezing
        thread = threading.Thread(target=self.run_scan_backend, args=(v_path, i_path, pad_before, pad_after, max_gap, min_scene, skip, vad_enabled, vad_buffer, vad_speaker_enabled, vad_speaker_threshold, mode), daemon=True)
        thread.start()

    def run_scan_backend(self, v_path, i_path, pad_before, pad_after, max_gap, min_scene, skip, vad_enabled, vad_buffer, vad_speaker_enabled, vad_speaker_threshold, mode):
        """Executed inside a background thread. Pushes events to the UI thread via queue."""
        try:
            self.generator = ScenePackGenerator(log_queue=self.log_queue, frame_skip=skip, mode=mode)
            self.scanned_intervals = self.generator.scan_and_prepare(Path(v_path), Path(i_path), pad_before, pad_after, max_gap, min_scene, vad_enabled, vad_buffer, vad_speaker_enabled, vad_speaker_threshold)
            logging.info(f"Finished Scanning! Found {len(self.scanned_intervals)} clips. Generating thumbnails...")
            
            import cv2
            from PIL import Image
            thumbnails = []
            cap = cv2.VideoCapture(v_path)
            for start, end, avg_x in self.scanned_intervals:
                cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
                ret, frame = cap.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame)
                    # Resize to thumbnail size while preserving aspect ratio
                    img.thumbnail((160, 90), Image.Resampling.LANCZOS)
                    thumbnails.append(img)
                else:
                    thumbnails.append(None)
            cap.release()
            
            self.log_queue.put(("progress", 1.0, "Scan Complete"))
            self.log_queue.put(("show_review_checklist", (self.scanned_intervals, thumbnails)))
        except Exception as e:
            logging.error(f"Error occurred during scan: {str(e)}")
            self.log_queue.put(("error", str(e)))
            self.log_queue.put(("progress", 0.0, "Scan Error Occurred"))
            self.log_queue.put(("reset_btn", None))

    def start_render(self):
        selected_intervals = []
        for i, (interval, var) in enumerate(self.review_checkboxes):
            if var.get():
                selected_intervals.append(interval)
        
        if not selected_intervals:
            messagebox.showerror("No Clips Selected", "Please select at least one clip to render.")
            return
            
        v_path = self.video_path_var.get()
        o_path = self.output_path_var.get()
        aspect_ratio = self.aspect_ratio_var.get()
        
        self._is_rendering = True
        self.btn_render.configure(state="disabled", text="Rendering...")
        self.log_queue.put(("progress", 0.0, "Extracting and rendering clips..."))
        
        thread = threading.Thread(target=self.run_render_backend, args=(v_path, o_path, selected_intervals, aspect_ratio), daemon=True)
        thread.start()
        
    def run_render_backend(self, v_path, o_path, intervals, aspect_ratio):
        try:
            self.generator.extract_and_concat(Path(v_path), intervals, Path(o_path), aspect_ratio)
            logging.info("Finished! Focus generation complete.")
            self.log_queue.put(("progress", 1.0, "Rendering Complete!"))
        except Exception as e:
            logging.error(f"Error occurred during render: {str(e)}")
            self.log_queue.put(("error", str(e)))
            self.log_queue.put(("progress", 0.0, "Render Error Occurred"))
        finally:
            self.log_queue.put(("reset_render_btn", None))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = FocusApp()
    app.mainloop()
