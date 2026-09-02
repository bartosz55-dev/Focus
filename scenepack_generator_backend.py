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
from typing import List, Tuple, Any, Optional, Dict, Union, Set, Callable
import urllib.request
import json
import numpy as np
import concurrent.futures
from PIL import Image, ImageDraw
import wave
import re
import gc

# Global lock for thread-safe model downloads and native C++ dlib operations
CASCADE_DOWNLOAD_LOCK = threading.Lock()
DLIB_THREAD_LOCK = threading.Lock()


def safe_face_locations(img, number_of_times_to_upsample=1, model="hog"):
    if img is None or getattr(img, 'size', 0) == 0:
        return []
    with DLIB_THREAD_LOCK:
        try:
            return face_recognition.face_locations(img, number_of_times_to_upsample=number_of_times_to_upsample, model=model)
        except Exception as e:
            logging.debug(f"safe_face_locations exception: {e}")
            return []


def safe_face_encodings(face_image, known_face_locations=None, num_jitters=1, model="small"):
    if face_image is None or getattr(face_image, 'size', 0) == 0:
        return []
    with DLIB_THREAD_LOCK:
        try:
            return face_recognition.face_encodings(face_image, known_face_locations=known_face_locations, num_jitters=num_jitters, model=model)
        except Exception as e:
            logging.debug(f"safe_face_encodings exception: {e}")
            return []


def safe_compare_faces(known_face_encodings, face_encoding_to_check, tolerance=0.6):
    if not known_face_encodings or face_encoding_to_check is None:
        return []
    with DLIB_THREAD_LOCK:
        try:
            return face_recognition.compare_faces(known_face_encodings, face_encoding_to_check, tolerance=tolerance)
        except Exception as e:
            logging.debug(f"safe_compare_faces exception: {e}")
            return []


def safe_face_landmarks(face_image, face_locations=None, model="large"):
    if face_image is None or getattr(face_image, 'size', 0) == 0:
        return []
    with DLIB_THREAD_LOCK:
        try:
            return face_recognition.face_landmarks(face_image, face_locations=face_locations, model=model)
        except Exception as e:
            logging.debug(f"safe_face_landmarks exception: {e}")
            return []


def safe_face_distance(face_encodings, face_to_compare):
    if not face_encodings or face_to_compare is None:
        return np.empty(0)
    with DLIB_THREAD_LOCK:
        try:
            return face_recognition.face_distance(face_encodings, face_to_compare)
        except Exception as e:
            logging.debug(f"safe_face_distance exception: {e}")
            return np.empty(0)



def get_cascade_classifier(cascade_path: Optional[str]):
    """
    Safely instantiates cv2.CascadeClassifier with robust fallbacks for PyInstaller bundled environments.
    Returns None safely if CascadeClassifier cannot be instantiated, avoiding runtime crashes.
    """
    if not cascade_path or not os.path.exists(cascade_path):
        return None

    try:
        if hasattr(cv2, 'CascadeClassifier'):
            clf = cv2.CascadeClassifier(cascade_path)
            if hasattr(clf, 'empty') and not clf.empty():
                return clf
        if hasattr(cv2, 'cv2') and hasattr(cv2.cv2, 'CascadeClassifier'):
            clf = cv2.cv2.CascadeClassifier(cascade_path)
            if hasattr(clf, 'empty') and not clf.empty():
                return clf
    except Exception as e:
        logging.warning(f"Could not load cv2.CascadeClassifier for path '{cascade_path}': {e}")
        return None

    return None


def extract_season_episode(path_obj: Any) -> Tuple[int, int, bool]:
    """
    Extracts (season, episode, has_explicit_tag) from filename or folder path.
    Supports formats: S01E02, Season 1 Episode 2, s1e02, 1x02, [Judas] Show - S02E01v2.mkv, etc.
    """
    p = Path(path_obj) if not isinstance(path_obj, Path) else path_obj
    full_str = f"{p.parent.name} {p.stem}".lower()

    # 1. Match S01E02, Season 1 Episode 2, S1-E02, S02.E01, S02E01v2
    m = re.search(r'(?:s|season\s*)[._\-\s]*(\d+)[._\-\s]*(?:e|ep|episode\s*)[._\-\s]*(\d+)', full_str)
    if m:
        return (int(m.group(1)), int(m.group(2)), True)

    # 2. Match 1x02, 02x05
    m = re.search(r'(\d+)x(\d+)', full_str)
    if m:
        return (int(m.group(1)), int(m.group(2)), True)

    # 3. Look for S01 / Season 1 separately
    m_s = re.search(r'(?:s|season\s*)[._\-\s]*(\d+)', full_str)
    season = int(m_s.group(1)) if m_s else 1
    has_season = bool(m_s)

    # Look for E01 / Episode 1 separately
    m_e = re.search(r'(?:e|ep|episode\s*)[._\-\s]*(\d+)', full_str)
    if m_e:
        return (season, int(m_e.group(1)), True)

    # 4. Fallback: find trailing episode number in stem
    nums = re.findall(r'\d+', p.stem)
    if nums:
        return (season, int(nums[-1]), has_season)

    return (season, 0, False)


def natural_sort_key(path_obj: Any) -> tuple:
    """
    Returns a natural alphanumeric sort key prioritizing Season (S01 -> S02 -> S03)
    and Episode (E01 -> E02 -> E10) before falling back to natural alphanumeric name.
    """
    p = Path(path_obj) if not isinstance(path_obj, Path) else path_obj
    name = p.name if hasattr(p, 'name') else str(p)
    season, episode, has_tag = extract_season_episode(p)
    alpha_key = [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', name)]
    if has_tag:
        return (0, season, episode, alpha_key)
    else:
        return (1, 0, 0, alpha_key)


def parse_video_paths(video_input: Any) -> List[Path]:
    """
    Normalizes a single path string, a list of strings/Paths, or a semicolon/comma-separated string into a naturally sorted list of resolved Path objects.
    """
    if not video_input:
        return []
    paths: List[Path] = []
    if isinstance(video_input, (list, tuple)):
        for item in video_input:
            if item:
                paths.append(Path(item).resolve())
    elif isinstance(video_input, (str, Path)):
        str_val = str(video_input).strip()
        if ";" in str_val:
            parts = [p.strip() for p in str_val.split(";") if p.strip()]
            paths = [Path(p).resolve() for p in parts]
        elif "," in str_val and not os.path.exists(str_val):
            parts = [p.strip() for p in str_val.split(",") if p.strip()]
            paths = [Path(p).resolve() for p in parts]
        else:
            paths = [Path(str_val).resolve()]
    
    unique_paths = list(dict.fromkeys(paths))
    return sorted(unique_paths, key=natural_sort_key)



def init_gpu_acceleration():
    """
    Enables OpenCV OpenCL hardware acceleration on supported GPUs (e.g. AMD Radeon RX 7800 XT, NVIDIA, Intel).
    Offloads image transformations, color conversions, and AI detection operations to the GPU.
    """
    try:
        if hasattr(cv2, 'ocl') and cv2.ocl.haveOpenCL():
            cv2.ocl.setUseOpenCL(False)
            logging.info("OpenCV OpenCL hardware acceleration has been explicitly disabled for thread safety.")
        else:
            logging.info("OpenCV OpenCL hardware acceleration is not supported on this platform/driver.")
    except Exception as e:
        logging.warning(f"Could not initialize OpenCV OpenCL acceleration: {e}")


def get_app_dir() -> Path:
    """Returns application logs directory in user Library/Logs folder on macOS or LocalAppData/Documents on Windows with fallback."""
    try:
        if platform.system() == "Darwin":
            app_dir = Path.home() / "Library" / "Logs" / "Focus"
        elif platform.system() == "Windows":
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                app_dir = Path(local_appdata) / "Focus" / "Logs"
            else:
                app_dir = Path.home() / "Documents" / "Focus_Logs"
        else:
            app_dir = Path.home() / ".focus" / "logs"

        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir
    except Exception:
        fallback_dir = Path(tempfile.gettempdir()) / "Focus_Logs"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir


def setup_crash_logger():
    """Configures file logging to focus_debug.log and hooks uncaught exceptions across threads."""
    try:
        log_file = get_app_dir() / "focus_debug.log"
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        file_handler.setLevel(logging.INFO)
        
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        if not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
            root_logger.addHandler(file_handler)

        def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            logging.critical("Uncaught Exception Encountered:", exc_info=(exc_type, exc_value, exc_traceback))

        def handle_thread_exception(args):
            logging.critical(f"Uncaught Thread Exception in '{args.thread.name}':", exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

        sys.excepthook = handle_uncaught_exception
        if hasattr(threading, 'excepthook'):
            threading.excepthook = handle_thread_exception

        logging.info(f"Persistent crash logger initialized at: {log_file}")
    except Exception as e:
        print(f"Could not setup crash logger: {e}")


# Initialize persistent crash logger
setup_crash_logger()

# Initialize OpenCV OpenCL GPU Acceleration
init_gpu_acceleration()

APP_VERSION = "v1.38"


class PlatformManager:
    """
    Clean OS-specific abstraction layer isolating Windows flags from macOS/POSIX.
    Ensures zero Windows-specific creationflags are ever injected on Darwin/macOS.
    """
    @staticmethod
    def is_windows() -> bool:
        return platform.system() == "Windows"

    @staticmethod
    def is_macos() -> bool:
        return platform.system() == "Darwin"

    @staticmethod
    def get_creation_flags() -> int:
        if PlatformManager.is_windows():
            return getattr(subprocess, "CREATE_NO_WINDOW", 0)
        return 0

    @staticmethod
    def get_subprocess_creation_flags() -> int:
        if platform.system() == "Windows":
            return getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        return 0

    @staticmethod
    def get_exe_suffix() -> str:
        if PlatformManager.is_windows():
            return ".exe"
        return ""

    @staticmethod
    def get_ffmpeg_safe_path(binary_name: str = "ffmpeg") -> str:
        return shutil.which(binary_name) or binary_name

    @staticmethod
    def write_concat_demuxer_manifest(file_list: List[Path], manifest_path: Path):
        write_concat_list(file_list, manifest_path)


CREATE_NO_WINDOW = PlatformManager.get_creation_flags()


def write_concat_list(chunk_paths: List[Path], concat_list_path: Path):
    """Writes a UTF-8 encoded FFmpeg concat demuxer list with normalized forward slashes."""
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for chunk_path in chunk_paths:
            if chunk_path:
                safe_path = str(chunk_path.resolve()).replace('\\', '/').replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")


TRANSLATIONS = {
    "English": {
        "dashboard": "Dashboard",
        "sec_workflow": "WORKFLOW",
        "sec_resources": "RESOURCES",
        "generator_tab": "Generator",
        "gallery_tab": "Beta / Character Gallery",
        "gallery_title": "Interactive Character Auto-Gallery (AI Detection)",
        "gallery_desc": "Pre-scan video to discover unique character faces. Click any card to select as target reference face!",
        "scan_chars": "Scan Video for Characters",
        "btn_cancel_gallery": "Cancel Scan",
        "how_to_use": "How to Use",
        "changelog": "Changelog",
        "settings_btn": "Settings",
        "settings_title": "Focus Preferences",
        "settings_appearance": "Appearance & Theme",
        "settings_accent": "Accent Color",
        "settings_lang": "Interface Language",
        "settings_sound": "Play sound notification when rendering finishes",
        "settings_default_mode": "Default Detection Mode:",
        "settings_done": "Done",
        "mode_dark": "Dark",
        "mode_light": "Light",
        "mode_system": "System (Auto)",
        "char_label": "Character",
        "detections_label": "detection(s)",
        "detections_badge": "{count} scene(s)",
        "preset_label": "Quick Presets:",
        "preset_auto": "✨ Auto-Tune",
        "preset_tiktok": "📱 TikTok / Shorts (9:16)",
        "preset_youtube": "🎬 YouTube (16:9)",
        "preset_draft": "🚀 Fast Draft Scan",
        "btn_auto_tune": "✨ Auto-Tune",
        "sel_video": "Select Input Video(s)...",
        "sel_folder": "Add Folder...",
        "clear": "Clear",
        "sel_ref": "Select Reference Face Image...",
        "sel_output": "Select Export Folder / Output...",
        "output_mode": "Output Mode:",
        "master_scenepack": "Master Scenepack (Single Video)",
        "separate_episodes": "Separate Episode Files",
        "audio_track": "Audio Track:",
        "sec_tuning": "Scene & Detection Tuning",
        "pad_before": "Padding Before Scene (s):",
        "pad_after": "Padding After Scene (s):",
        "max_gap": "Max Gap / Blink Tolerance (s):",
        "min_scene": "Min Scene Length (s):",
        "frame_skip": "Frame Skip Interval:",
        "aspect_label": "Aspect Ratio & Framing:",
        "export_quality": "Export Quality:",
        "vad_enable": "Smart Dialogue Protection (VAD / Lip-Sync)",
        "vad_buffer": "Silence Snapping Buffer (ms):",
        "vad_speaker_enable": "Target Speaker Voice Matching (Filter Background/Narrator)",
        "vad_speaker_threshold": "Similarity Threshold:",
        "skip_intro_enable": "Skip Intro (OP)",
        "skip_outro_enable": "Skip Outro (ED)",
        "intro_mode_title": "Detection Engine:",
        "intro_mode_auto": "Auto Chapters (MKV/MP4)",
        "intro_mode_90s": "First 90s (Standard OP)",
        "intro_mode_custom": "Custom Duration",
        "intro_duration_lbl": "Duration (s):",
        "generate": "Step 1: Start Scan & Analyze Video",
        "review_title": "Step 2: Review & Select Detected Scenes",
        "btn_render": "Step 2: Render & Export Selected Clips",
        "logs_title": "Real-Time Execution Logs & Diagnostics:",
        "play_orig": "Play Original Video",
        "play_result": "Play Result",
        "no_video": "No video selected",
        "no_image": "No image selected",
        "no_output": "No save location selected",
        "err_no_human_face": "No human face found in reference image '{name}'. If you selected a 2D Anime character, please switch detection mode to 'Anime'!",
        "ready": "Ready to generate",
        "real_faces": "Real Faces (Live-Action / 3D)",
        "anime": "2D Animation / Anime",
        "aspect_16_9": "16:9 Original (Widescreen)",
        "aspect_9_16_vert": "9:16 Vertical (Auto-Track Subject)",
        "aspect_9_16_blur": "9:16 Vertical (Blurred Background)",
        "th_include": "Include",
        "th_thumb": "Thumbnail",
        "th_start": "Start Time",
        "th_end": "End Time",
        "th_duration": "Duration (s)",
        "tutorial_title": "How to Use Focus",
        "tutorial_close": "Got it!",
        "tutorial_body": (
            "• Supported Formats:\n"
            "  • Video: MP4, MKV, MOV, AVI, WEBM, FLV, M4V, TS, WMV\n"
            "  • Images: PNG, JPG, JPEG, WEBP, BMP, TIFF\n\n"
            "• Workflow 1 (Auto-Gallery Beta):\n"
            "  1. Open the 'Beta / Character Gallery' tab.\n"
            "  2. Click 'Scan Video for Characters' to auto-discover unique faces.\n"
            "  3. Click any character card to set it as your target reference face!\n\n"
            "• Workflow 2 (Manual Selection):\n"
            "  1. Select your input video file(s) or folder.\n"
            "  2. Choose a clear reference face image.\n"
            "  3. Choose the output save location.\n"
            "  4. Click 'Step 1: Start Scan & Analyze Video'.\n"
            "  5. Review detected clips in Step 2 and click 'Render & Export'!\n\n"
            "• Framing Formats:\n"
            "  • 16:9 Original: Preserves original widescreen source.\n"
            "  • 9:16 Vertical (Auto-Track): Auto-centers and tracks face for TikTok/Shorts.\n"
            "  • 9:16 Blurred Background: Overlays 16:9 video onto blurred vertical canvas."
        ),
        "changelog_title": "Project History & Changelog",
        "changelog_close": "Close"
    },
    "Polski": {
        "dashboard": "Panel Główny",
        "sec_workflow": "PROJEKT / WORKFLOW",
        "sec_resources": "MATERIAŁY",
        "generator_tab": "Generator Scen",
        "gallery_tab": "Galeria Postaci (Beta)",
        "gallery_title": "Interaktywna Galeria Postaci (Wykrywanie AI)",
        "gallery_desc": "Przeskanuj plik wideo, aby automatycznie wykryć unikalne twarze postaci. Kliknij dowolną kartę, aby wybrać cel!",
        "scan_chars": "Skanuj Wideo w Poszukiwaniu Postaci",
        "btn_cancel_gallery": "Anuluj Skanowanie",
        "how_to_use": "Instrukcja Obsługi",
        "changelog": "Historia Zmian",
        "settings_btn": "Ustawienia",
        "settings_title": "Ustawienia Focus",
        "settings_appearance": "Wygląd i Motyw",
        "settings_accent": "Kolor Wiodący",
        "settings_lang": "Język Interfejsu",
        "settings_sound": "Odtwórz dźwięk po zakończeniu renderowania",
        "settings_default_mode": "Domyślny Tryb Detekcji:",
        "settings_done": "Gotowe",
        "mode_dark": "Ciemny (Dark)",
        "mode_light": "Jasny (Light)",
        "mode_system": "Systemowy (Auto)",
        "char_label": "Postać",
        "detections_label": "wykryć",
        "detections_badge": "{count} ujęć",
        "preset_label": "Szybkie Profile:",
        "preset_auto": "✨ Auto-Tune",
        "preset_tiktok": "📱 TikTok / Rolki (9:16)",
        "preset_youtube": "🎬 YouTube (16:9)",
        "preset_draft": "🚀 Szybki Szkic (Draft)",
        "btn_auto_tune": "✨ Auto-Tune",
        "sel_video": "Wybierz Plik(i) Wideo...",
        "sel_folder": "Dodaj Folder...",
        "clear": "Wyczyść",
        "sel_ref": "Wybierz Twarz Referencyjną...",
        "sel_output": "Wybierz Folder Docelowy / Zapisz Jako...",
        "output_mode": "Tryb Wyjściowy:",
        "master_scenepack": "Pojedynczy Master Scenepack",
        "separate_episodes": "Osobne Pliki dla Odcinków",
        "audio_track": "Ścieżka Dźwiękowa:",
        "sec_tuning": "Dostrajanie Scen i Detekcji",
        "pad_before": "Margines Przed Sceną (s):",
        "pad_after": "Margines Po Scenie (s):",
        "max_gap": "Tolerancja Przerw / Mrugnięć (s):",
        "min_scene": "Min. Długość Sceny (s):",
        "frame_skip": "Krok Analizy Klatek:",
        "aspect_label": "Format i Kadrowanie:",
        "export_quality": "Jakość Renderowania:",
        "vad_enable": "Inteligentna Ochrona Dialogów (VAD / Lip-Sync)",
        "vad_buffer": "Bufor Ciszy (ms):",
        "vad_speaker_enable": "Dopasowanie Głosu Postaci (Filtr Tła)",
        "vad_speaker_threshold": "Próg Podobieństwa Głosu:",
        "skip_intro_enable": "Pomiń Intro (OP)",
        "skip_outro_enable": "Pomiń Outro (ED)",
        "intro_mode_title": "Silnik Wykrywania:",
        "intro_mode_auto": "Automatycznie z Rozdziałów (MKV/MP4)",
        "intro_mode_90s": "Pierwsze 90s (Standard Anime OP)",
        "intro_mode_custom": "Własny Czas Trwania",
        "intro_duration_lbl": "Czas Trwania (s):",
        "generate": "Krok 1: Rozpocznij Skanowanie & Analizę Wideo",
        "review_title": "Krok 2: Przegląd i Wybór Wykrytych Scen",
        "btn_render": "Krok 2: Wyrenderuj Wybrane Klipy",
        "logs_title": "Dziennik Zdarzeń & Diagnostyka:",
        "play_orig": "Odtwórz Oryginał",
        "play_result": "Odtwórz Wynik",
        "no_video": "Nie wybrano wideo",
        "no_image": "Nie wybrano zdjęcia referencyjnego",
        "no_output": "Nie wybrano miejsca zapisu",
        "err_no_human_face": "Nie znaleziono ludzkiej twarzy w zdjęciu referencyjnym '{name}'. Jeśli wybrałeś postać z Anime (np. Marin Kitagawa), przełącz tryb detekcji na 'Anime'!",
        "ready": "Gotowy do generowania",
        "real_faces": "Prawdziwe Twarze (Filmy / Seriale)",
        "anime": "Anime / Animacja 2D",
        "aspect_16_9": "16:9 Oryginalny (Szeroki Ekran)",
        "aspect_9_16_vert": "9:16 Pionowy (Śledzenie Postaci)",
        "aspect_9_16_blur": "9:16 Pionowy (Rozmyte Tło)",
        "th_include": "Dołącz",
        "th_thumb": "Miniatura",
        "th_start": "Początek",
        "th_end": "Koniec",
        "th_duration": "Długość (s)",
        "tutorial_title": "Instrukcja Obsługi Focus",
        "tutorial_close": "Zrozumiałem!",
        "tutorial_body": (
            "• Obsługiwane Formaty:\n"
            "  • Wideo: MP4, MKV, MOV, AVI, WEBM, FLV, M4V, TS, WMV\n"
            "  • Obrazy: PNG, JPG, JPEG, WEBP, BMP, TIFF\n\n"
            "• Metoda 1 (Automatyczna Galeria Beta):\n"
            "  1. Przejdź do zakładki 'Galeria Postaci (Beta)'.\n"
            "  2. Kliknij 'Skanuj Wideo w Poszukiwaniu Postaci', aby automatycznie wykryć twarze.\n"
            "  3. Kliknij dowolną postać, aby ustawić ją jako cel generowania!\n\n"
            "• Metoda 2 (Ręczny Wybór):\n"
            "  1. Wybierz plik(i) wideo wejściowego lub cały folder.\n"
            "  2. Wybierz wyraźne zdjęcie referencyjne twarzy postaci.\n"
            "  3. Wskaż miejsce zapisu scenepacka.\n"
            "  4. Kliknij 'Krok 1: Rozpocznij Skanowanie i Analizę'.\n"
            "  5. Przejrzyj wykryte sceny w tabeli i kliknij 'Krok 2: Wyrenderuj Wybrane Klipy'!\n\n"
            "• Formaty Obrazu:\n"
            "  • 16:9 Oryginalny: Wyciąga sceny w pełnym, oryginalnym kadrze wideo.\n"
            "  • 9:16 Pionowy (Śledzenie): Dynamicznie podąża za twarzą postaci (TikTok/Reels/Shorts).\n"
            "  • 9:16 Rozmyte Tło: Wyśrodkowane wideo 16:9 nałożone na estetycznie rozmyte tło."
        ),
        "changelog_title": "Historia Projektu i Zmiany",
        "changelog_close": "Zamknij"
    },
    "Deutsch": {
        "dashboard": "Dashboard",
        "sec_workflow": "WORKFLOW",
        "sec_resources": "RESSOURCEN",
        "generator_tab": "Generator",
        "gallery_tab": "Charakter-Galerie (Beta)",
        "how_to_use": "Anleitung",
        "changelog": "Änderungsprotokoll",
        "settings_btn": "Einstellungen",
        "settings_title": "Focus Einstellungen",
        "settings_appearance": "Erscheinungsbild",
        "settings_accent": "Akzentfarbe",
        "settings_lang": "Sprache",
        "settings_sound": "Signalton bei Fertigstellung abspielen",
        "settings_done": "Fertig",
        "mode_dark": "Dunkel",
        "mode_light": "Hell",
        "mode_system": "System (Auto)",
        "sel_video": "Eingabevideo auswählen...",
        "sel_ref": "Referenzgesicht auswählen...",
        "sel_output": "Exportordner auswählen...",
        "generate": "Schritt 1: Video analysieren & scannen",
        "btn_render": "Schritt 2: Ausgewählte Clips exportieren",
        "review_title": "Ergebnisse überprüfen",
        "logs_title": "Diagnose & Protokolle:",
        "real_faces": "Echte Gesichter (Live-Action / 3D)",
        "anime": "2D Animation / Anime",
        "ready": "Bereit"
    },
    "Español": {
        "dashboard": "Panel Principal",
        "sec_workflow": "FLUJO DE TRABAJO",
        "sec_resources": "RECURSOS",
        "generator_tab": "Generador",
        "gallery_tab": "Galería de Personajes (Beta)",
        "how_to_use": "Instrucciones",
        "changelog": "Historial de Cambios",
        "settings_btn": "Configuración",
        "settings_title": "Preferencias de Focus",
        "settings_appearance": "Apariencia",
        "settings_accent": "Color de Acento",
        "settings_lang": "Idioma",
        "settings_sound": "Reproducir sonido al finalizar",
        "settings_done": "Listo",
        "mode_dark": "Oscuro",
        "mode_light": "Claro",
        "mode_system": "Sistema (Auto)",
        "sel_video": "Seleccionar video(s)...",
        "sel_ref": "Seleccionar rostro de referencia...",
        "sel_output": "Seleccionar carpeta de exportación...",
        "generate": "Paso 1: Analizar y Escanear Video",
        "btn_render": "Paso 2: Renderizar Clips Seleccionados",
        "review_title": "Revisar Escenas Detectadas",
        "logs_title": "Registros de Diagnóstico:",
        "real_faces": "Rostros Reales (Películas / Series)",
        "anime": "Animación 2D / Anime",
        "ready": "Listo"
    },
    "Français": {
        "dashboard": "Tableau de Bord",
        "sec_workflow": "WORKFLOW",
        "sec_resources": "RESSOURCES",
        "generator_tab": "Générateur",
        "gallery_tab": "Galerie de Personnages (Bêta)",
        "how_to_use": "Mode d'Emploi",
        "changelog": "Journal des Modifications",
        "settings_btn": "Paramètres",
        "settings_title": "Préférences Focus",
        "settings_appearance": "Mode d'Apparence",
        "settings_accent": "Couleur d'Accent",
        "settings_lang": "Langue",
        "settings_sound": "Jouer un son à la fin du rendu",
        "settings_done": "Terminé",
        "mode_dark": "Sombre",
        "mode_light": "Clair",
        "mode_system": "Système (Auto)",
        "sel_video": "Sélectionner vidéo(s)...",
        "sel_ref": "Sélectionner visage de référence...",
        "sel_output": "Dossier d'exportation...",
        "generate": "Étape 1 : Analyser la Vidéo",
        "btn_render": "Étape 2 : Rendre les Clips",
        "review_title": "Vérifier les Scènes Détectées",
        "logs_title": "Journaux d'Exécution :",
        "real_faces": "Visages Réels (Films / Séries)",
        "anime": "Animation 2D / Anime",
        "ready": "Prêt",
        "tutorial_title": "Comment Utiliser Focus",
        "tutorial_body": (
            "• Étape 1 : Ajoutez un ou plusieurs fichiers vidéo.\n\n"
            "• Étape 2 : Sélectionnez une image nette du visage de référence.\n\n"
            "• Étape 3 : Choisissez le mode Visages Réels ou Anime.\n\n"
            "• Étape 4 : Ajustez les marges et les filtres audio VAD.\n\n"
            "• Étape 5 : Lancez l'analyse et exportez vos scènes !"
        ),
        "changelog_title": "Historique du Projet & Modifications",
        "changelog_close": "Fermer"
    },
    "日本語": {
        "dashboard": "ダッシュボード",
        "sec_workflow": "ワークフロー",
        "sec_resources": "リソース",
        "appearance": "外観モード:",
        "theme": "カラーテーマ:",
        "language": "言語:",
        "play_sound": "完了時に音を鳴らす",
        "how_to_use": "使い方",
        "changelog": "更新履歴",
        "sel_video": "入力動画を選択",
        "sel_ref": "参照顔画像を選択",
        "sel_output": "出力先フォルダを選択",
        "pad_before": "前パディング(秒):",
        "pad_after": "後パディング(秒):",
        "max_gap": "最大許容間隔(秒):",
        "frame_skip": "フレームスキップ間隔:",
        "generate": "ステップ1: 動画スキャン・解析開始",
        "review": "結果の確認:",
        "play_orig": "元の動画を再生",
        "play_result": "結果を再生",
        "no_video": "動画が選択されていません",
        "no_image": "画像が選択されていません",
        "no_output": "保存先が選択されていません",
        "ready": "生成の準備ができました",
        "real_faces": "実写顔 (Live-Action / 3D)",
        "anime": "2D アニメーション / アニメ",
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


def get_translation(lang_name: str, key: str) -> Any:
    """Safely retrieves a localized string with fallback to English and clean formatted string."""
    lang_dict = TRANSLATIONS.get(lang_name, TRANSLATIONS.get("English", {}))
    if key in lang_dict:
        return lang_dict[key]
    val = TRANSLATIONS.get("English", {}).get(key)
    if val is not None:
        return val
    if key.startswith("sec_"):
        return key.replace("sec_", "").replace("_", " ").upper()
    return key


def get_changelog_text(lang_name: str = "English") -> str:
    """Return complete multi-version scrollable changelog text for the given language."""
    if lang_name in ("Polski", "Polish"):
        return (
            f"=== Historia Wersji i Zmiany Projektu Focus ({APP_VERSION}) ===\n\n"
            "• v1.38 (Ujednolicenie Wersjonowania i Czysty Nagłówek / Clean Header & Standardized Decimal Versioning):\n"
            "  - Usunięto zbędne kontrolki z górnego paska nawigacyjnego, przywracając czysty i minimalistyczny nagłówek (dostęp do wszystkich motywów, kolorów i języków odbywa się przez dedykowane okno Preferencji w pasku bocznym).\n"
            "  - Wprowadzono precyzyjny, dwumiejscowy system numeracji wersji w całym projekcie i changelogu (np. v1.30 + 0.01 = v1.31 ... v1.99 + 0.01 = v2.00).\n\n"
            "• v1.37 (Szybkie Przełączniki i Płynne Style / Dynamic Live Styling Architecture):\n"
            "  - Zapewniono natychmiastową, dynamiczną zmianę stylów i motywów dla całej aplikacji i otwartych okien dialogowych bez konieczności restartu.\n\n"
            "• v1.36 (Domyślny Język Angielski i Tryb Ciemny / Default English & Dark Mode Theme):\n"
            "  - Ustawiono domyślny motyw wizualny na 'Tryb Ciemny (Dark Mode)' oraz domyślny język interfejsu na angielski (English).\n"
            "  - Zaktualizowano profile konfiguracyjne i skróty startowe.\n\n"
            "• v1.35 (Domyślny Język Systemowy i Motyw Systemowy / System Locale & Auto Theme Sync):\n"
            "  - Ustawiono domyślny motyw wizualny na 'Systemowy (System Auto-Sync)', automatycznie dostosowujący się do jasnego/ciemnego motywu macOS i Windows.\n"
            "  - Wdrożono automatyczne wykrywanie języka systemowego z płynnym mapowaniem i bezpiecznym fallbackiem do języka angielskiego (English).\n"
            "  - Zaktualizowano domyślne profile konfiguracji i dialog preferencji.\n\n"
            "• v1.34 (Kompleksowy Szlif UI/UX i Poprawki Wizualne / Comprehensive UI/UX Polish Pass):\n"
            "  - Wyeliminowano wycieki surowych nazw zmiennych (np. 'sec_workflow') oraz ujednolicono nagłówki sekcji paska bocznego (WORKFLOW / MATERIAŁY).\n"
            "  - Poszerzono pasek boczny do 240px i zoptymalizowano marginesy, całkowicie eliminując ucinanie tekstu przycisku '✨ Galeria Postaci (Beta)'.\n"
            "  - Zdeduplikowano nawigację: usunięto zbędne przyciski zakładek z nagłówka, czyniąc pasek boczny jedynym, spójnym źródłem nawigacji.\n"
            "  - Przebudowano siatkę dostrajania scen i detekcji na precyzyjny 3-kolumnowy układ QGridLayout z idealnym wyrównaniem etykiet i pól tekstowych.\n"
            "  - Uporządkowano kontrolki audio i rozdziałów: pogrupowano ochronę dialogów (VAD / Lip-Sync), filtr głosu oraz pomijanie Intro/Outro w estetyczne, zwarte wiersze.\n"
            "  - Zwiększono kontrast i wysokość pasków podglądu ścieżek plików, nadając im nowoczesny wygląd czytelnych paneli.\n"
            "  - Poprawiono literówki i ujednolicono teksty przycisków głównych akcji we wszystkich językach.\n\n"
            "• v1.33 (Hotfix Startu / Startup Fix):\n"
            "  - Naprawiono błąd NameError (brakujący import 'Union' z biblioteki typing), który powodował crash podczas uruchamiania skompilowanej aplikacji na macOS i Windows.\n"
            "  - Zweryfikowano bezbłędny start GUI oraz zgodność modułów na wszystkich platformach.\n\n"
            "• v1.32 (Nowe Okno Ustawień i Motywy / Dedicated Preferences Dialog & Theme System):\n"
            "  - Dodano nowoczesne, dedykowane okno ustawień (Preferences Dialog) w stylu macOS/Apple HIG z wizualnym wyborem motywu, 8 kolorami akcentu, językiem i zachowaniem.\n"
            "  - Wdrożono pełną obsługę Trybu Jasnego (Light Mode), Ciemnego (Dark Mode) oraz Automatycznego/Systemowego z dopracowanymi arkuszami stylów QSS.\n"
            "  - Uporządkowano i odchudzono pasek boczny (Sidebar), usuwając przeładowane kontrolki i eliminując ucinanie tekstu.\n"
            "  - Całkowicie przebudowano i uzupełniono słownik tłumaczeń w języku polskim i angielskim, usuwając nienaturalne zwroty i błędy podwójnych znaków ampersand.\n\n"
            "• v1.31 (Sortowanie Chronologiczne Sezonów i Odcinków / Multi-Season Chronological Sorting):\n"
            "  - Wprowadzono hierarchiczny analizator nazw i sezonów (`extract_season_episode`): pliki są teraz w pierwszej kolejności precyzyjnie grupowane według Sezonów (S01 -> S02 -> S03 -> ...), a wewnątrz sezonów według numerów odcinków (E01 -> E02 -> ... -> E24).\n"
            "  - Prawidłowo sortuje odcinki nawet przy różnych tytułach w obrębie serii (np. 'Sono Bisque Doll wa Koi wo Suru S01' przed 'KiseKoi S02').\n\n"
            "• v1.30 (Inteligentne Dopasowanie Bitrate do Źródła / Auto Source Bitrate Matching):\n"
            "  - Dodano inteligentny tryb 'Auto (Dopasuj do źródła / Match Source Bitrate)' – automatycznie bada strumień wideo (ffprobe) i dopasowuje docelowy bitrate do pliku wejściowego z bezpiecznym zapasem 15%.\n"
            "  - Wyeliminowano niepotrzebne puchnięcie plików (zamiast 500 MB ze skompresowanego odcinka 300 MB, scenepack zajmuje teraz proporcjonalne ~60-80 MB przy zachowaniu idealnej ostrości źródła).\n"
            "  - Uporządkowano i zoptymalizowano profile jakości: Auto (Match Source - domyślny), Maximum (Master / 35M), High (Crystal Clear / 20M), Medium (10M), Draft (4M).\n\n"
            "• v1.29 (Renderowanie Master Quality i Bitrate / Crystal Clear Master Rendering):\n"
            "  - Całkowicie wyeliminowano pikselozę i kompresję makroblokową: przeprojektowano kontrolę bitrate sprzętowego akceleratora VideoToolbox (Apple Silicon), NVENC i QSV.\n"
            "  - Zwiększono domyślny bitrate eksportu do 25-35 Mbps z adaptacyjnym współczynnikiem jakości (-q:v 75-85 / CRF 14-17), zapewniając krystalicznie ostry, bezstratny obraz w dynamicznych scenach i anime.\n"
            "  - Wprowadzono nowe profile jakości w GUI: Maximum (Master / 35M), High (Crystal Clear / 25M - domyślny), Medium (Standard / 16M), Draft (8M).\n\n"
            "• v1.28 (Silnik Pomijania Intro i Outro / Skip Opening & Ending Engine):\n"
            "  - Dodano zaawansowany przełącznik i silnik usuwania/pomijania Intro (Opening / OP) oraz Outro (Ending / ED).\n"
            "  - Wdrożono dwuwarstwowy detektor: automatyczny odczyt metadanych rozdziałów MKV/MP4 przez ffprobe (tagi 'Opening', 'Intro', 'OP', 'NCOP', 'Credits', 'Ending', itp.) z inteligentnym fallbackiem na okno 90 sekund (standardowe anime OP).\n"
            "  - Zintegrowano pomijanie dekodowania klatek w oknie Intro bezpośrednio w pętli skanera wideo (15% szybsza analiza odcinków) oraz automatyczne odcinanie nakładających się scen.\n"
            "  - Dodano dedykowane kontrolki w karcie ustawień GUI oraz obsługę własnego czasu trwania w sekundach.\n\n"
            "• v1.27 (Wieloregionowe Rozpoznawanie Anime / Multi-Region Anime Palette Matching):\n"
            "  - Całkowicie przebudowano wektor cech anime: dodano analizę górnego obszaru fryzury/włosów (45% wysokości) oraz pełnej palety kolorystycznej głowy, eliminując gubienie postaci przez wycinanie wyłącznie wewnętrznego owalu skóry.\n"
            "  - Zwiększono rozdzielczość skanowania klatek do 640px w trybie Anime oraz zoptymalizowano czułość detekcji kaskadowej (scaleFactor=1.06, minNeighbors=3, minSize=16px), wyłapując ujęcia średnie i z profilu.\n"
            "  - Dodano automatyczny fallback przy ładowaniu obrazu referencyjnego (avatary/ikony), eliminując fałszywe błędy braku detekcji twarzy w obrazie wejściowym.\n\n"
            "• v1.26 (Naturalne Sortowanie Odcinków i Ochrona Cięć / Natural Episode Sorting):\n"
            "  - Wprowadzono naturalne sortowanie odcinków (Human/Episode Natural Order S01E01 -> S01E02 -> ... -> S01E24) przy wyborze wielu plików i całych folderów.\n"
            "  - Zabezpieczono granice scen przed wyciekaniem do innych postaci: rozszerzanie VAD zostało ściśle ograniczone do maksymalnie 2.5s oraz zablokowane na najbliższych cięciach montażowych kamery (Scene Cuts).\n"
            "  - Wyeliminowano niekontrolowane kilkuminutowe wydłużanie klipów podczas ciągłych dialogów innych postaci lub muzyki w tle.\n\n"
            "• v1.25 (Szybka Detekcja Anime i FFmpeg Demux / Zero-Lock Anime Recognition):\n"
            "  - Wyeliminowano wąskie gardło dlib CNN w trybie Anime: detekcja postaci anime odbywa się teraz w pełni równolegle przez czysty NumPy i kaskady OpenCV (ponad 4000x szybsza analiza klatek anime).\n"
            "  - Dodano precyzyjne dopasowanie cech anime (`is_anime_feature_match`) powiązane z suwakiem czułości Tolerance.\n"
            "  - Zoptymalizowano flagi FFmpeg dla analizy ciszy (`-vn -sn -dn`) i cięć scen (`-an -sn -dn`), eliminując wszelkie niepotrzebne strumienie.\n\n"
            "• v1.24 (Synchronizacja Changelogu i Czcionki Systemowe / In-App Changelog Sync):\n"
            "  - Uzupełniono pełną historię wersji w oknie Changelog aplikacji od v1.13 do najnowszej.\n"
            "  - Wdrożono dynamiczny dobór czcionki systemowej (San Francisco na macOS, Segoe UI na Windows).\n\n"
            "• v1.23 (Optymalizacja UI i Licznik Postępu Wsadowego / Unified Media Hub):\n"
            "  - Uporządkowano i odchudzono interfejs użytkownika, usuwając zbędne banery i duplikujące się panele.\n"
            "  - Wdrożono jedno zintegrowane centrum zarządzania plikami (Unified Media Hub) dla pojedynczych plików, wielu odcinków i całych folderów.\n"
            "  - Dodano wskaźnik i licznik postępu wielu odcinków (np. '🎬 Episode [2/24]: ...') oraz dwuwarstwowy pasek postępu.\n"
            "  - Przyspieszono analizę ciszy VAD o 10x-20x na odcinek dzięki pomijaniu dekodowania wideo (-vn w FFmpeg).\n"
            "  - Przyspieszono wykrywanie cięć scen o 10x dzięki filtrowi wstępnego skalowania klatek (scale=320:-1).\n"
            "  - Zwiększono liczbę wątków równoległego renderowania do min(6, cpu_count) z bieżącym podglądem postępu.\n\n"
            "• v1.22 (Bezpieczne Wątki i Wsparcie Wielu Wideo / Master Concat Safety):\n"
            "  - Naprawiono import `MasterConcatWorker` w GUI Qt eliminując potencjalny błąd NameError podczas scalania scenepacka.\n"
            "  - Wprowadzono bezpieczne parsowanie wielu ścieżek wideo (`parse_video_paths`) w selektorze audio i galerii postaci.\n"
            "  - Naprawiono anulowanie skanowania galerii (`GalleryScanWorker.cancel`).\n\n"
            "• v1.21 (Automatyczne Rozszerzanie Granic Scen / Scene Boundary Auto-Expansion):\n"
            "  - Zaimplementowano automatyczne rozszerzanie granic sceny wstecz (`start = max(0.0, start - needed)`) przy końcu filmu, gwarantując spełnienie minimalnego czasu trwania sceny.\n\n"
            "• v1.20 (Ikona Paska Zadań Windows i Obsługa Błędów / Windows Taskbar Icon):\n"
            "  - Naprawiono rejestrację ikony aplikacji na pasku zadań systemu Windows 11 (AppUserModelID).\n"
            "  - Zabezpieczono globalną obsługę wyjątków i logowanie awarii w GUI Qt.\n\n"
            "• v1.19 (Kadrowanie Pionowe 9:16 i Rozmyte Tło / Aspect Ratio Smart Canvas):\n"
            "  - Dodano obsługę proporcji pionowych 9:16 z inteligentnym śledzeniem twarzy i rozmyciem tła.\n\n"
            "• v1.18 (Ochrona Dialogów Lip-Sync VAD i Głos / VAD & Voice Matching):\n"
            "  - Wdrożono inteligentną ochronę zdań (VAD) oraz dopasowywanie głosu wybranej postaci (MFCC Voice Print).\n\n"
            "• v1.17 (Silnik Profili Auto-Tune / Auto-Tune Preset Engine):\n"
            "  - Dodano silnik automatycznego doboru optymalnych parametrów wykrywania dla trybów Anime oraz Real Faces.\n\n"
            "• v1.16 (Wybór Ścieżek Audio / Multi-Audio Track Selector):\n"
            "  - Dodano wybór ścieżek dźwiękowych w plikach MKV/MP4 z wieloma strumieniami audio.\n\n"
            "• v1.15 (Automatyczna Galeria Postaci / Character Discovery Gallery):\n"
            "  - Wprowadzono galerię automatycznego wykrywania i klastrowania unikalnych postaci z filmu.\n\n"
            "• v1.14 (Nowoczesny Ciemny Interfejs Studio / Modern Dark Studio UI):\n"
            "  - Wdrożono nowoczesny, ciemny styl interfejsu (Modern Studio Layout) z powiadomieniami Toast.\n\n"
            "• v1.13 (Migracja na PySide6 Qt 6 / Qt 6 Engine Migration):\n"
            "  - Przepisano cały interfejs graficzny na framework Qt 6 (PySide6) z architekturą asynchronicznych workerów.\n\n"
            "• v1.12 (Przebudowa Przetwarzania Wsadowego / Batch Queue Engine Overhaul):\n"
            "  - Naprawiono błąd 'Tag Mismatch' w sygnałach Qt (`show_render_success` vs `render_complete`), który powodował zatrzymanie przetwarzania wsadowego po 1 odcinku.\n"
            "  - Zaimplementowano brakującą klasę `MiniPreviewDialog` (eliminacja błędu `NameError` przy kliknięciu przycisku Podgląd).\n"
            "  - Zezwolono na automatyczne kontynuowanie kolejki wsadowej w przypadku braku wykrytych twarzy lub błędu w konkretnym pliku wideo.\n"
            "  - Dodano automatyczne rozszerzenie kodowania w scalaniu głównym (Master Concat Fallback), gdy połączenie bezprzetwarzaniowe nie powiedzie się.\n"
            "  - Zabezpieczono zamykanie aplikacji przed wymuszonym killowaniem wątków C++ (`QThread.terminate()`).\n\n"
            "• v1.11 (Poprawki Wycieków Pamięci i OOM / Memory Leak Fixes):\n"
            "  - Naprawiono błąd SIGSEGV (brak pamięci w dlib) podczas ładowania bardzo dużych materiałów wideo.\n"
            "  - Usunięto przetrzymywanie ogromnych obrazów w pamięci podręcznej podczas wstępnego skanowania twarzy.\n"
            "  - Zredukowano liczbę równoległych wątków skanujących i wdrożono Garbage Collection.\n\n"
            "• v1.10 (Stabilność Procesów w Tle / Subprocess Stability Overhaul):\n"
            "  - Rozwiązano problem z procesami potomnymi i zwalnianiem zasobów przy przerwaniu kodowania sprzętowego.\n"
            "  - Naprawiono wycieki plików tymczasowych VAD audio.\n"
            "  - Przebudowano asynchroniczne scalanie 'Master Scenepack', odblokowując GUI.\n\n"
            "• v1.09 (Pobieranie Kaskad SSL i Profile Jakości / SSL Download & Quality Settings):\n"
            "  - Naprawiono błąd SSL (CERTIFICATE_VERIFY_FAILED) podczas pobierania detektora twarzy Anime z GitHuba.\n"
            "  - Dodano opcję 'Jakość eksportu' pozwalającą na wybór High (CRF 16), Medium (CRF 20) lub Low (CRF 24).\n\n"
            "• v1.08 (Przepisanie MFCC na Czysty NumPy / Pure NumPy MFCC Rewrite):\n"
            "  - Zastąpiono `scipy` i `python_speech_features` przez czysty NumPy dla uniknięcia błędów dyld na macOS.\n\n"
            "• v1.07 (Zachowanie Dowiązań Symbolicznych / PyInstaller Symlinks Fix):\n"
            "  - Naprawiono tworzenie archiwów .zip dla macOS (zachowanie symlinków w paczce .app).\n\n"
            "• v1.06 (Lokalizacja Logów w ~/Library/Logs / Logs Relocation):\n"
            "  - Przeniesiono logi do ~/Library/Logs/Focus by spełniać wymagania restrykcji TCC.\n\n"
            "• v1.05 (Odblokowanie Kwarantanny macOS / Gatekeeper Auto-Unquarantine):\n"
            "  - Dodano system auto-unquarantine (odblokowanie z kwarantanny) na macOS.\n\n"
            "• v1.04 (Uruchamianie Bezkonsolowe / Zero-Terminal Launch):\n"
            "  - Wdrożono uruchamianie aplikacji bez otwierania okna terminala w tle.\n\n"
            "• v1.03 (Poprawka Obcinania Etykiet UI / UI Text Clipping Fix):\n"
            "  - Naprawiono ucięte etykiety tekstu w interfejsie graficznym.\n\n"
            "• v1.02 (Poprawka Znaku & w Profilach / Ampersand UI Fix):\n"
            "  - Naprawiono błąd wyświetlania znaku '&' w nazwach profili szybkościowych.\n\n"
            "• v1.01 (Łatki Bezpieczeństwa / Stability & Security Fixes):\n"
            "  - Aplikacja otrzymała ogólne łatki stabilności i bezpieczeństwa ECC.\n\n"
            "• v1.00 (Wydanie Główne PySide6 Studio / Production Release):\n"
            "  - Kompleksowa migracja interfejsu do nowoczesnego środowiska PySide6 (Qt 6) Studio.\n"
            "  - Bezobsługowe skrypty startowe dla systemów Windows (.bat) i macOS (.command).\n"
            "  - Wyrafinowana typografia UI, czytelne etykiety oraz ulepszony układ elementów.\n"
            "  - Wzbogacone wsparcie wielojęzyczne (polski, angielski, niemiecki, hiszpański, francuski, japoński, rosyjski, ukraiński).\n"
            "  - Sprzętowo akcelerowane wycinanie i scalanie fragmentów wideo przez FFmpeg.\n"
            "  - Interaktywna Galeria Postaci (AI Detection) umożliwiająca automatyczne wstępne skanowanie twarzy.\n\n"
            "=== Wersje Początkowe (v0.01 – v0.95) ===\n\n"
            "• v0.95 – Skonsolidowano kompilację Windows do pojedynczego pliku Focus.exe (--onefile) i naprawiono motywy kolorystyczne.\n"
            "• v0.94 – Naprawiono błąd CascadeClassifier w PyInstaller i dodano bezkonsolowy launcher VBScript dla Windows.\n"
            "• v0.93 – Automatyczne bezobsługowe launchery: dodano Uruchom_Focus.command (macOS) oraz Uruchom_Focus.bat (Windows).\n"
            "• v0.92 – Naprawa reguł wyzwalania wydań CI/CD GitHub Release.\n"
            "• v0.91 – Krytyczna poprawka uruchamiania na Windows: dodano wymaganie scipy i ukryte importy PyInstaller.\n"
            "• v0.90 – Poprawka uprawnień wydań GitHub CI/CD: dodano uprawnienia zapisu dla generowania informacji o wydaniu.\n"
            "• v0.89 – Uniwersalna akceleracja sprzętowa: dynamiczne wykrywanie GPU (NVENC/QSV/AMF/MF oraz VideoToolbox).\n"
            "• v0.88 – Pełny port wieloplatformowy Windows 10/11 & macOS z automatycznym pobieraniem FFmpeg.\n"
            "• v0.87 – Przygotowanie repozytorium do otwartego wydania open-source GitHub.\n"
            "• v0.86 – Naprawiono błędy podpróbkowania obrazu (czarne linie) przy kadrowaniu 9:16 w FFmpeg.\n"
            "• v0.85 – Wdrożono automatycznie przewijane okno logów oraz dynamiczne przyciski postępu.\n"
            "• v0.84 – Wdrożono odciski głosowe postaci (Target Speaker Voice Fingerprinting) filtrujące osoby spoza kadru.\n"
            "• v0.83 – Kompleksowa przebudowa UI/UX inspirowana nowoczesnymi ciemnymi pulpitami nawigacyjnymi.\n"
            "• v0.81 – Wdrożono ekstrakcję miniaturek klatek wideo przez OpenCV w liście podglądu scen.\n"
            "• v0.80 – Wdrożono pionowe kadrowanie 9:16 (Auto-Track i rozmyte tło) oraz dwufazową listę weryfikacji.\n"
            "• v0.79 – Wdrożono detekcję aktywności głosowej AI (VAD) i przyciąganie cięć do pauz w wypowiedziach.\n"
            "• v0.74 – Naprawiono obcinanie dźwięku i zaniki audio przez wyrównanie bufora apad i resamplera 48kHz.\n"
            "• v0.72 – Dodano algorytm Smart Auto-Tune i dynamiczne profile (Anime, Cinematic, Fast Edits).\n"
            "• v0.71 – Naprawiono zamrażanie klatek wideo i brak synchronizacji przez stałe resamplowanie PTS (-fps_mode cfr).\n"
            "• v0.70 – Wewnętrzne aktualizacje stabilności oraz drobne szlify interfejsu.\n"
            "• v0.67 – Przywrócono brakujący import concurrent.futures rozwiązujący NameError w równoległym wycinaniu.\n"
            "• v0.66 – Udoskonalono grupowanie twarzy Anime z histogramem 1D Hue i 256-bitowym dopasowaniem dHash.\n"
            "• v0.65 – Dodano etap grupowania i deduplikacji twarzy po skanowaniu z wyborem najlepszej miniaturki.\n"
            "• v0.64 – Naprawiono renderowanie ikony aplikacji w macOS Dock oraz dodano eliptyczne maskowanie twarzy Anime.\n"
            "• v0.63 – Naprawiono brakujący import PIL Image w skanerze galerii postaci.\n"
            "• v0.62 – Udoskonalono Galerię Postaci Anime z użyciem histogramów 2D HSV i cech dHash.\n"
            "• v0.61 – Wdrożono drugi przebieg scalania dla deduplikacji postaci w Galerii Beta.\n"
            "• v0.60 – Naprawiono zawieszanie skanera w Galerii Beta i podłączono kolejkę zdarzeń.\n"
            "• v0.59 – Naprawiono błąd lokalizacji trybu Beta w nieangielskich wersjach językowych UI.\n"
            "• v0.58 – Przeniesiono skanowanie postaci do wielowątkowego pracownika w tle (krok 2.5s).\n"
            "• v0.57 – Wprowadzono Galerię Postaci Beta z automatycznym wykrywaniem i wyborem postaci jednym kliknięciem.\n"
            "• v0.56 – Naprawiono awarię podczas uruchamiania aplikacji przez zmianę kolejności inicjalizacji zmiennych.\n"
            "• v0.55 – Naprawiono początkowe zamrażanie strumienia wideo (5s) przez bufory -accurate_seek i filtr min. czasu (1.0s).\n"
            "• v0.54 – Głęboki audyt kodu: dynamiczne podpowiedzi (tooltips) i bezpieczne kolejki UI.\n"
            "• v0.53 – Naprawiono odświeżanie tekstów podpowiedzi oraz mapowanie nazw motywów koloristycznych.\n"
            "• v0.52 – Pełny audyt kodu i refaktoryzacja: wymuszenie niemutowalności ustawień i walidacji wejścia.\n"
            "• v0.51 – Wyodrębniono czysty wektorowy symbol aparatu z ikonka.png dla kafli macOS Dock.\n"
            "• v0.50 – Dodano dynamiczny generator ikon macOS squircle dla Docka i nagłówka okna.\n"
            "• v0.49 – Zaktualizowano źródło ikon do ikonka.png i zregenerowano natywne zasoby icon.icns.\n"
            "• v0.48 – Dodano wsparcie dla natywnych ikon aplikacji macOS (icon.icns) w skrypcie budowania.\n"
            "• v0.47 – Wyeliminowano zacięcia wideo i rozjazd audio przy łączeniu fragmentów (zamknięte GOPy, genpts, moov faststart).\n"
            "• v0.46 – Zoptymalizowano proces budowania aplikacji: wykluczono zbędne zależności i zmniejszono rozmiar paczki.\n"
            "• v0.45 – Naprawiono regresję układu GUI przez usunięcie zduplikowanej ramki ustawień.\n"
            "• v0.44 – Kompleksowy audyt kodu (poprawki wycieków uchwytów cv2.VideoCapture, ucieczki ścieżek concat).\n"
            "• v0.43 – Dodano tolerancję przerw / mrugnięć (1.5s) zapobiegającą zbyt wczesnym cięciom przy obracaniu głowy.\n"
            "• v0.42 – Naprawiono problemy z renderowaniem i stylami okien CTkToplevel na macOS.\n"
            "• v0.41 – Naprawiono utratę stanu przycisków segmentowanych przy zmianie języka.\n"
            "• v0.40 – Pełne tłumaczenia i18n interfejsu (tryby wyglądu, kolory, podpowiedzi, samouczek).\n"
            "• v0.39 – Dodano obsługę wielu języków (polski, angielski, niemiecki, rosyjski, ukraiński, hiszpański, francuski, japoński).\n"
            "• v0.38 – Wymuszono regułę wersjonowania (+0.01 per prompt) oraz potok filtrów setpts/asetpts.\n"
            "• v0.37 – Hybrydowe szybkie wyszukiwanie (-ss przed -i) + filtry resetujące PTS dla idealnej synchronizacji A/V.\n"
            "• v0.36 – Rozszerzono szczegółowe śledzenie historii wydań projektu.\n"
            "• v0.35 – Zcentralizowano zmienną APP_VERSION we wszystkich oknach i nagłówkach.\n"
            "• v0.34 – Dodano wbudowane okno Changelogu z początkową historią zmian.\n"
            "• v0.33 – Dokładne wyszukiwanie klatek (-ss po -i) naprawiające zawieszanie klipów MKV.\n"
            "• v0.32 – Zoptymalizowano pozycjonowanie parametrów szybkiego wyszukiwania w FFmpeg.\n"
            "• v0.31 – Równoległe wycinanie fragmentów wideo z użyciem ThreadPoolExecutor (5-10x szybsze renderowanie).\n"
            "• v0.30 – Dodano flagę -start_at_zero i zweryfikowano granice marginesu padding_after.\n"
            "• v0.29 – Wymuszono stałą liczbę klatek na sekundę (CFR -r 24 -fps_mode cfr) i wyrównanie kluczowych klatek GOP.\n"
            "• v0.28 – Skonfigurowano identyfikator pakietu Focus (com.focus.app) w PyInstaller build.py.\n"
            "• v0.27 – Konwersja przewodnika obsługi do czytelnego CTkTextbox z zawijaniem wierszy.\n"
            "• v0.26 – Nagłówek User-Agent GitHub dla pobierania klasyfikatorów XML oraz walidacja rozmiaru (>50KB).\n"
            "• v0.25 – Dodano walidację ładowania kaskad OpenCV cascade.empty().\n"
            "• v0.24 – Przeniesiono pliki wykonywalne i XML do ~/Library/Application Support/Focus dla bezpieczeństwa macOS.\n"
            "• v0.23 – Dodano podpowiedzi dla trybów Real Faces i Anime.\n"
            "• v0.22 – Dodano tryb detekcji twarzy Anime w OpenCV z użyciem lbpcascade_animeface.\n"
            "• v0.21 – Naprawiono błąd AttributeError zakresu metod GUI przy uruchamianiu.\n"
            "• v0.20 – Dodano wyskakujące okno samouczka 'How to Use'.\n"
            "• v0.19 – Dodano flagi synchronizacji czasu audio (-avoid_negative_ts make_zero, -fflags +genpts, -async 1).\n"
            "• v0.18 – Poprawka rozsynchronizowania długości wideo/audio przez ponowne kodowanie AAC.\n"
            "• v0.17 – Oficjalny rebranding aplikacji na 'Focus'.\n"
            "• v0.16 – Trwały zapis ustawień w pliku JSON (~/.scenepack_generator_settings.json).\n"
            "• v0.15 – Zintegrowano natywne powiadomienie dźwiękowe po zakończeniu w macOS (afplay).\n"
            "• v0.14 – Dodano własny silnik motywów kolorystycznych (generate_themes.py).\n"
            "• v0.13 – Naprawiono artefakty szarych klatek kluczowych przez usunięcie kopiowania strumieni (-c copy).\n"
            "• v0.12 – Sprzętowa akceleracja GPU Apple Silicon VideoToolbox (-c:v h264_videotoolbox).\n"
            "• v0.11 – Dodano logikę łączenia strumieni wideo (concat demuxer).\n"
            "• v0.10 – Początkowa logika wycinania fragmentów wideo przez FFmpeg.\n"
            "• v0.09 – Parametr regulacji tolerancji rozpoznawania twarzy.\n"
            "• v0.08 – Kontrola interwału pomijania klatek (Frame Skip) dla optymalizacji prędkości.\n"
            "• v0.07 – Numeryczna konfiguracja marginesów przed i po scenie (Padding Before/After).\n"
            "• v0.06 – Pasek postępu i wskaźnik procentowy w czasie rzeczywistym z szacowanym czasem ETA.\n"
            "• v0.05 – Wybór lokalizacji zapisu pliku wyjściowego i konfiguracja nazwy.\n"
            "• v0.04 – Wybór obrazu referencyjnego i podgląd miniaturki.\n"
            "• v0.03 – Wybór pliku wideo wejściowego i wyświetlanie ścieżki.\n"
            "• v0.02 – Utworzenie podstawowego układu graficznego w CustomTkinter.\n"
            "• v0.01 – Początkowy prototyp CLI do wycinania scen wideo na podstawie rozpoznawania twarzy."
        )
    else:
        return (
            f"=== Focus Project Changelog & Version History ({APP_VERSION}) ===\n\n"
            "• v1.38 (Clean Header & Standardized Decimal Versioning):\n"
            "  - Removed redundant quick switcher controls from the top header bar, restoring a clean and minimal header layout (all themes, colors, and languages remain conveniently accessible in the dedicated Preferences modal via the sidebar).\n"
            "  - Standardized strict two-decimal version numbering across all project components and changelog entries (e.g. v1.30 + 0.01 = v1.31 ... v1.99 + 0.01 = v2.00).\n\n"
            "• v1.37 (Quick Switchers & Dynamic Live Styling Architecture):\n"
            "  - Enabled live application-wide dynamic theme, color, and stylesheet transitions without requiring application restarts.\n\n"
            "• v1.36 (Default English Language & Dark Mode Theme):\n"
            "  - Configured default visual appearance mode to Dark Mode and default interface language to English.\n"
            "  - Synchronized default configuration profiles and desktop launch scripts.\n\n"
            "• v1.35 (System-Detected Language & System Theme by Default):\n"
            "  - Configured default appearance mode to 'System', automatically matching the operating system's Dark/Light mode theme.\n"
            "  - Implemented automatic system language detection with graceful fallback to English across all platforms.\n"
            "  - Synchronized default configuration profiles and Preferences modal.\n\n"
            "• v1.34 (Comprehensive UI/UX Polish & Visual Bug-Fix Pass):\n"
            "  - Resolved raw variable leaks (such as 'sec_workflow') and styled sidebar section headers with clean uppercase typography.\n"
            "  - Expanded sidebar width to 240px with adjusted padding, eliminating all text truncation on '✨ Beta / Character Gallery'.\n"
            "  - Deduplicated navigation by removing redundant header tab buttons, keeping the sidebar as the single source of navigation truth.\n"
            "  - Re-engineered Scene & Detection Tuning into a strict 3-column QGridLayout with baseline-aligned labels and unified control heights.\n"
            "  - Restructured audio & chapter detection controls into clean horizontal groups: VAD dialogue protection, target voice matching slider, and Intro/Outro skip engine.\n"
            "  - Enhanced input path displays with increased padding, higher contrast, and modern text readout styling.\n"
            "  - Fixed string typos and standardized action button labels across all localization dictionaries.\n\n"
            "• v1.33 (Startup Hotfix):\n"
            "  - Fixed NameError (missing 'Union' import from typing module) that caused application startup crashes on macOS and Windows.\n"
            "  - Verified clean startup and runtime module compatibility across all platforms.\n\n"
            "• v1.32 (UI/UX Overhaul, Dedicated Settings Window, Light/Dark Modes & Translation Polish):\n"
            "  - Introduced modern Apple/macOS-styled Preferences Dialog with visual appearance picker, 8 vibrant accent colors, language switcher, and audio notification controls.\n"
            "  - Added complete, responsive Light Mode, Dark Mode, and System Theme Auto-Sync with refined QSS stylesheets.\n"
            "  - Decluttered sidebar navigation, eliminated horizontal text truncation, and fixed all double-ampersand display bugs.\n"
            "  - Thoroughly overhauled and aligned all Polish and English localization strings.\n\n"
            "• v1.31 (Multi-Season & Multi-Title Chronological Media Sorting):\n"
            "  - Implemented hierarchical season/episode metadata parser (`extract_season_episode`): video files are strictly ordered by Season (S01 -> S02 -> S03 -> ...) and then Episode (E01 -> E02 -> ... -> E24).\n"
            "  - Accurately sorts multi-season releases even with differing title conventions across seasons (e.g. 'Sono Bisque Doll wa Koi wo Suru S01' before 'KiseKoi S02').\n\n"
            "• v1.30 (Intelligent Auto-Matching Source Bitrate & Proportional File Sizes):\n"
            "  - Added intelligent 'Auto (Match Source Bitrate)' mode: dynamically probes input stream bitrate via ffprobe and mirrors it with a +15% safety headroom.\n"
            "  - Completely eliminated bloated file sizes (scenepacks from 300MB episodes now weigh ~60-80MB while perfectly preserving source quality).\n"
            "  - Optimized quality presets in GUI: Auto (Match Source - default), Maximum (Master / 35M), High (Crystal Clear / 20M), Medium (10M), Draft (4M).\n\n"
            "• v1.29 (Crystal Clear / Master Quality Video Rendering & Bitrate Overhaul):\n"
            "  - Completely eliminated macroblocking and pixelation artifacts: overhauled rate control and bitrate headroom for Apple Silicon VideoToolbox, NVENC, and QSV hardware encoders.\n"
            "  - Upgraded default rendering profile to 25-35 Mbps with adaptive quality factor (-q:v 75-85 / CRF 14-17), delivering studio-grade crystal clear 1080p scenepacks even during fast motion and particle-heavy anime scenes.\n"
            "  - Introduced new export quality profiles in GUI: Maximum (Master / 35M), High (Crystal Clear / 25M - default), Medium (Standard / 16M), Draft (8M).\n\n"
            "• v1.28 (Intelligent Intro & Outro Removal Engine / Skip Opening):\n"
            "  - Added intelligent Intro (Opening / OP) and Outro (Ending / ED) skipping engine to exclude theme songs and credit sequences from scenepacks.\n"
            "  - Dual-layer detector: reads MKV/MP4 embedded chapter markers via ffprobe ('Opening', 'Intro', 'OP', 'NCOP', 'Credits', 'Ending', etc.) with smart 90s fallback window (standard anime OP length).\n"
            "  - Bypasses frame decoding inside intro ranges during the video scan pass (15% faster scan) and automatically prunes/trims overlapping clips.\n"
            "  - Added settings card controls in the Qt GUI with auto chapter mode, fixed 90s mode, and custom duration options.\n\n"
            "• v1.27 (Hair/Palette Multi-Region Anime Recognition & Avatar Reference Fallback):\n"
            "  - Completely re-engineered anime character feature vectors: added upper hair/bangs region (45% height) and full head palette analysis, preventing character drop caused by discarding hair colors.\n"
            "  - Scaled frame scan resolution to 640px in Anime mode and optimized cascade sensitivity (scaleFactor=1.06, minNeighbors=3, minSize=16px) to capture medium and profile shots.\n"
            "  - Implemented automatic fallback when loading reference images (avatars/icons), eliminating false 'target face not found' errors.\n\n"
            "• v1.26 (Natural Chronological Episode Sorting & Strict Scene Cut Boundary Protection):\n"
            "  - Implemented human-intuitive natural episode sorting (S01E01 -> S01E02 -> ... -> S01E24) across multi-file and folder imports.\n"
            "  - Protected scene boundaries against character leakage: VAD sentence extension is strictly capped to 2.5s and bounded by nearest shot cuts.\n"
            "  - Prevented clips from bloating into multi-minute sequences during long dialogue of other characters or continuous background music.\n\n"
            "• v1.25 (Zero-Lock Anime Recognition & Ultra-Fast FFmpeg Demuxing):\n"
            "  - Eliminated dlib CNN lock bottleneck in Anime mode: character recognition now runs completely in parallel via pure NumPy histograms and OpenCV cascades (over 4,000x faster frame scan).\n"
            "  - Integrated dynamic anime feature sensitivity (`is_anime_feature_match`) controlled by the Tolerance slider.\n"
            "  - Optimized FFmpeg demuxing flags for VAD silence analysis (`-vn -sn -dn`) and scene cuts (`-an -sn -dn`).\n\n"
            "• v1.24 (Full In-App Changelog Synchronization & Native System Font Provider):\n"
            "  - Updated complete in-app changelog dialog history from v1.13 through the latest release.\n"
            "  - Implemented dynamic platform system fonts (.AppleSystemUIFont on macOS, Segoe UI on Windows).\n\n"
            "• v1.23 (UI Streamlining, Multi-Episode Progress Counter & VAD Acceleration):\n"
            "  - Streamlined and decluttered user interface, removing static banners and redundant preset panels.\n"
            "  - Introduced Unified Media & Reference Hub supporting single videos, multi-selection, and folder imports.\n"
            "  - Added real-time multi-episode progress monitor (e.g. '🎬 Episode [2/24]: ...') with dual-tier progress bars.\n"
            "  - Accelerated VAD silence detection 10x-20x per episode by skipping video decoding (-vn in FFmpeg).\n"
            "  - Accelerated scene cut boundary detection 10x via frame downscaling filter (scale=320:-1).\n"
            "  - Scaled parallel segment extraction workers dynamically up to min(6, cpu_count).\n\n"
            "• v1.22 (MasterConcatWorker Import Fix & Multi-Video Gallery/Audio Support):\n"
            "  - Fixed `MasterConcatWorker` import in Qt GUI preventing potential NameError during master scenepack concatenation.\n"
            "  - Added multi-video path normalization (`parse_video_paths`) to audio stream selector and gallery scan.\n"
            "  - Fixed cancellation handling in `GalleryScanWorker.cancel()`.\n\n"
            "• v1.21 (Scene Boundary Auto-Expansion & Quality Pass):\n"
            "  - Implemented backward auto-expansion in `merge_intervals()` to guarantee `min_scene_duration` is always met.\n\n"
            "• v1.20 (Windows Taskbar Icon & Exception Safety Pass):\n"
            "  - Fixed Windows 11 taskbar icon registration via explicit AppUserModelID setup.\n"
            "  - Hardened global exception handler and persistent crash logger.\n\n"
            "• v1.19 (Aspect Ratio Smart Canvas & 9:16 Blurred Background):\n"
            "  - Added support for 9:16 vertical crop with face auto-tracking and blurred background rendering.\n\n"
            "• v1.18 (Lip-Sync VAD & Speaker Similarity Matching):\n"
            "  - Implemented smart sentence boundary snapping (VAD) and MFCC speaker voice matching.\n\n"
            "• v1.17 (Auto-Tune Preset Engine):\n"
            "  - Introduced intelligent Auto-Tune engine for automatic parameter tuning across Anime and Real Faces modes.\n\n"
            "• v1.16 (Multi-Audio Track Selector):\n"
            "  - Added multi-audio stream detection and track selection for MKV/MP4 files.\n\n"
            "• v1.15 (Automated Character Discovery Gallery):\n"
            "  - Introduced automated background character discovery and facial clustering gallery.\n\n"
            "• v1.14 (Modern Dark Studio UI Overhaul):\n"
            "  - Overhauled UI styling with dark modern studio layout and non-blocking toast notifications.\n\n"
            "• v1.13 (PySide6 / Qt 6 Engine Migration):\n"
            "  - Migrated entire desktop UI to PySide6 (Qt 6) with asynchronous worker thread architecture.\n\n"
            "• v1.12 (Batch Queue Engine Overhaul & Full Stability Fix):\n"
            "  - Fixed Qt signal tag mismatch (`show_render_success` vs `render_complete`) that caused batch queue to halt after 1 episode.\n"
            "  - Implemented missing `MiniPreviewDialog` class (fixed `NameError` crash when clicking Preview button).\n"
            "  - Added auto-advancing non-blocking batch queue workflow on 0 clips detected or individual file errors.\n"
            "  - Implemented robust re-encoding fallback for Master Concat when stream copy fails.\n"
            "  - Hardened UI thread shutdown against unsafe C++ thread terminations.\n\n"
            "• v1.11 (OOM & Memory Leak Fixes):\n"
            "  - Fixed critical SIGSEGV (Out of Memory in dlib) when loading very large video assets.\n"
            "  - Eliminated massive in-memory caching of PIL images during pre-scan phase.\n"
            "  - Capped concurrent facial scanning threads and introduced periodic Garbage Collection.\n\n"
            "• v1.10 (Major Stability & Backend Overhaul):\n"
            "  - Eliminated 'Zombie Subprocess' memory leaks during interrupted hardware encoding.\n"
            "  - Fixed VAD audio temp file leaks and tuple unpacking errors.\n"
            "  - Refactored 'Master Scenepack' concatenation to asynchronous mode, unblocking the UI.\n"
            "  - Added missing validations for reference images in Anime mode.\n"
            "  - Hardened UI against destructive interactions during Batch Processing.\n\n"
            "• v1.09 (SSL Download Fix & Export Quality Setting):\n"
            "  - Fixed SSL CERTIFICATE_VERIFY_FAILED error when downloading Anime face detector from GitHub.\n"
            "  - Added 'Export Quality' option allowing users to select High (CRF 16), Medium (CRF 20), or Low (CRF 24).\n\n"
            "• v1.08 (NumPy MFCC Rewrite):\n"
            "  - Completely replaced `scipy` and `python_speech_features` dependencies with a pure NumPy MFCC extraction implementation.\n\n"
            "• v1.07 (PyInstaller Symlinks Fix):\n"
            "  - Fixed PyInstaller macOS zipping process (`zip -ry`) to preserve symlinks in the app bundle.\n\n"
            "• v1.06 (Logs Relocation):\n"
            "  - Relocated logs to `~/Library/Logs/Focus` to bypass macOS TCC restrictions.\n\n"
            "• v1.05 (Gatekeeper Bypass):\n"
            "  - Implemented silent Gatekeeper auto-unquarantining on macOS.\n\n"
            "• v1.04 (Zero-Terminal Launch):\n"
            "  - Implemented zero-terminal macOS launching.\n\n"
            "• v1.03 (UI Text Clipping Fix):\n"
            "  - Resolved UI layout text clipping bugs.\n\n"
            "• v1.02 (Ampersand UI Fix):\n"
            "  - Fixed ampersand mnemonics rendering bugs in profile names.\n\n"
            "• v1.01 (Stability Improvements):\n"
            "  - Applied general ECC stability patches across the codebase.\n\n"
            "• v1.00 (Production Release):\n"
            "  - Complete UI migration to PySide6 (Qt 6) with Modern Dark Studio interface.\n"
            "  - Automated Zero-Terminal Setup & Launcher for Windows (.bat) and macOS (.sh).\n"
            "  - Refined UI typography, professional labels, and polished layout.\n"
            "  - Robust multi-language support (English, Polish, German, Spanish, French, Japanese, Russian, Ukrainian).\n"
            "  - Hardware-accelerated FFmpeg scene extraction and concatenation.\n"
            "  - Interactive Character Auto-Gallery (AI Detection) for face pre-scanning.\n\n"
            "=== Legacy Development History (v0.01 – v0.95) ===\n\n"
            "• v0.95 – Consolidated Windows build to a single standalone Focus.exe (--onefile mode) eliminating redundant launcher files and DLL clutter. Fixed UI color theme persistence across view navigation.\n"
            "• v0.94 – Fix OpenCV CascadeClassifier missing attribute error in PyInstaller builds and added Windows VBScript zero-console launcher.\n"
            "• v0.93 – Zero-Terminal Automated Launchers: added double-clickable Uruchom_Focus.command (macOS Gatekeeper auto-clear) and Uruchom_Focus.bat (Windows).\n"
            "• v0.92 – CI/CD Release Trigger Fix: restored tag trigger pattern in release workflows.\n"
            "• v0.91 – Critical Windows Execution Fix: added explicit scipy requirement and PyInstaller hidden imports.\n"
            "• v0.90 – CI/CD GitHub Release Permissions Fix: added explicit write permissions for release notes generation.\n"
            "• v0.89 – Universal Hardware Acceleration Support: dynamic runtime probing for GPU video encoders across Windows (NVENC/QSV/AMF/MF) and macOS (VideoToolbox).\n"
            "• v0.88 – Full cross-platform port for Windows 10/11 & macOS with automated FFmpeg static binary downloading.\n"
            "• v0.87 – Prepared repository for open-source GitHub release: sanitized local system paths and added comprehensive documentation.\n"
            "• v0.86 – Fixed FFmpeg sub-sampling rendering errors (black line artifacts) on 9:16 crops and unified interface color elements.\n"
            "• v0.85 – Implemented auto-scrolling log window and dynamic percent progress buttons.\n"
            "• v0.84 – Implemented Target Speaker Voice Fingerprinting: profiles character voice from verified face frames and filters out non-target speakers.\n"
            "• v0.83 – Complete UI/UX overhaul inspired by modern dark web dashboards with custom Tkinter animation loops.\n"
            "• v0.81 – Implemented thumbnail extraction via OpenCV to display video frame previews alongside the checklist.\n"
            "• v0.80 – Implemented 9:16 Vertical Cropping (Auto-Track & Blurred Background), FFmpeg Scene Cut Snapping, and two-phase Interactive Clip Review Checklist.\n"
            "• v0.79 – Implemented AI Voice Activity Detection (VAD) & Active Speaker Alignment to intelligently extend scenes to the nearest silence pause.\n"
            "• v0.74 – Fixed random audio truncation and dropouts by implementing Audio Frame Padding (apad) and 48kHz audio resampler alignment.\n"
            "• v0.72 – Added Smart Auto-Tune algorithm and dynamic Presets (Anime, Cinematic, Fast Edits).\n"
            "• v0.71 – Fixed video freezing & PTS desynchronization via constant frame rate resampling (-fps_mode cfr).\n"
            "• v0.70 – Internal stability updates and minor UI refinements.\n"
            "• v0.67 – Restored missing concurrent.futures import fixing NameError in parallel slicing.\n"
            "• v0.66 – Enhanced Anime face clustering with 1D Hue histograms and 256-bit dHash matching.\n"
            "• v0.65 – Added post-scan face clustering and deduplication with best thumbnail selection.\n"
            "• v0.64 – Fixed macOS Dock icon rendering and added elliptical Anime face masking.\n"
            "• v0.63 – Fixed missing PIL Image import in character gallery scanner.\n"
            "• v0.62 – Upgraded Anime Character Gallery using 2D HSV histograms and dHash features.\n"
            "• v0.61 – Implemented 2nd pass merge for duplicate characters in Beta Gallery.\n"
            "• v0.60 – Fixed Beta Gallery scanner freeze and connected event queue.\n"
            "• v0.59 – Fixed Beta Mode localization bug in non-English UI languages.\n"
            "• v0.58 – Moved character scanning to multi-threaded background worker (2.5s step).\n"
            "• v0.57 – Introduced Beta Character Gallery with auto-detection & 1-click selection.\n"
            "• v0.56 – Fixed startup crash by reordering variable initialization.\n"
            "• v0.55 – Fixed initial 5s video freeze via -accurate_seek buffers & min scene filter (1.0s).\n"
            "• v0.54 – Deep Code Audit: Dynamic tooltips & safe UI queues.\n"
            "• v0.53 – Fixed tooltip refresh & color theme name mappings.\n"
            "• v0.52 – Full code audit & refactor: enforced immutable settings & input validation.\n"
            "• v0.51 – Extracted clean camera vector symbol from ikonka.png for macOS Dock tiles.\n"
            "• v0.50 – Added dynamic macOS squircle icon generator for Dock & window header.\n"
            "• v0.49 – Updated icon asset source to ikonka.png and regenerated native icon.icns.\n"
            "• v0.48 – Added native macOS app icon support (icon.icns) in build script.\n"
            "• v0.47 – Fixed video freezing & audio drift on segment concatenation (closed GOPs, genpts, moov faststart).\n"
            "• v0.46 – Optimized build process: excluded unnecessary dependencies and reduced package size.\n"
            "• v0.45 – Fixed GUI layout regression by removing duplicate settings frame.\n"
            "• v0.44 – Comprehensive code audit (cv2.VideoCapture handle leak fixes, concat path escapes).\n"
            "• v0.43 – Added gap/blink tolerance (1.5s) to prevent premature cuts during head turning.\n"
            "• v0.42 – Fixed macOS CTkToplevel window rendering and styling issues.\n"
            "• v0.41 – Fixed segmented button state loss on language change.\n"
            "• v0.40 – Complete i18n UI translations (appearance modes, colors, tooltips, tutorial).\n"
            "• v0.39 – Added multi-language support (Polish, English, German, Russian, Ukrainian, Spanish, French, Japanese).\n"
            "• v0.38 – Enforced permanent versioning rule (+0.01 per prompt) & setpts/asetpts filter pipeline.\n"
            "• v0.37 – Hybrid Fast Seeking (-ss before -i) + PTS Reset Filters for perfect A/V sync.\n"
            "• v0.36 – Expanded detailed project release history tracking.\n"
            "• v0.35 – Centralized APP_VERSION variable across all windows and headers.\n"
            "• v0.34 – Added built-in Changelog window with initial change history.\n"
            "• v0.33 – Accurate frame seeking (-ss after -i) fixing MKV clip freezing.\n"
            "• v0.32 – Optimized FFmpeg fast seeking parameter positioning.\n"
            "• v0.31 – Parallel video slicing using ThreadPoolExecutor (5-10x faster render).\n"
            "• v0.30 – Added -start_at_zero flag and verified padding_after clip boundary logic.\n"
            "• v0.29 – Enforced Constant Frame Rate (CFR -r 24 -fps_mode cfr) & GOP keyframe alignment (-g 24).\n"
            "• v0.28 – Configured PyInstaller build.py with Focus bundle identifier (com.focus.app).\n"
            "• v0.27 – Converted How-to-Use guide to read-only CTkTextbox with word wrapping.\n"
            "• v0.26 – GitHub User-Agent header fix for XML downloads & size validation (>50KB check).\n"
            "• v0.25 – Added OpenCV cascade.empty() load validation.\n"
            "• v0.24 – Relocated external binaries and XML to ~/Library/Application Support/Focus for macOS bundle security.\n"
            "• v0.23 – Tooltip helpers for Real Faces vs Anime modes.\n"
            "• v0.22 – Added OpenCV Anime face detection mode using lbpcascade_animeface classifier.\n"
            "• v0.21 – Fixed GUI method scope AttributeError on application startup.\n"
            "• v0.20 – Added 'How to Use' tutorial Toplevel popup window.\n"
            "• v0.19 – Audio sync timestamp flags (-avoid_negative_ts make_zero, -fflags +genpts, -async 1).\n"
            "• v0.18 – Audio/Video duration drift fix using AAC re-encoding (-c:a aac -b:a 192k).\n"
            "• v0.17 – Official application rebranding to 'Focus'.\n"
            "• v0.16 – Persistent JSON settings storage (~/.scenepack_generator_settings.json).\n"
            "• v0.15 – Integrated macOS native completion audio notification (afplay).\n"
            "• v0.14 – Added custom color theme engine (generate_themes.py).\n"
            "• v0.13 – Fixed keyframe gray smearing artifacts by removing stream copying (-c copy).\n"
            "• v0.12 – VideoToolbox Apple Silicon GPU hardware acceleration (-c:v h264_videotoolbox).\n"
            "• v0.11 – Added stream concat demuxer logic.\n"
            "• v0.10 – Initial FFmpeg segment extraction logic.\n"
            "• v0.09 – Face Recognition tolerance adjustment parameter.\n"
            "• v0.08 – Frame Skip interval speed optimization control.\n"
            "• v0.07 – Padding Before & Padding After numerical configuration.\n"
            "• v0.06 – Progress bar and real-time scanning percentage ETA indicator.\n"
            "• v0.05 – Output save location selector & filename configuration.\n"
            "• v0.04 – Reference Image picker & preview integration.\n"
            "• v0.03 – Input Video file picker & path display integration.\n"
            "• v0.02 – Basic CustomTkinter GUI layout creation.\n"
            "• v0.01 – Initial CLI prototype for face recognition scenepack cutting."
        )




def canonicalize_mode(mode_str: str) -> str:
    """Converts any localized mode string to 'Real Faces' or 'Anime'."""
    if not mode_str:
        return "Real Faces"
    for lang_dict in TRANSLATIONS.values():
        anime_val = lang_dict.get("anime")
        if isinstance(anime_val, str) and mode_str.strip().lower() in [anime_val.lower(), "anime", "аниме"]:
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
    Extracts a 2D HS hair histogram, 2D HS full-head histogram, and 256-bit perceptual dHash feature vector from an anime face crop.
    """
    if crop_bgr is None or crop_bgr.size == 0:
        return None
    h, w = crop_bgr.shape[:2]

    # 1. Hair / Top region (top 45% of crop)
    hair_crop = crop_bgr[0:max(1, int(h * 0.45)), :]
    hsv_hair = cv2.cvtColor(hair_crop, cv2.COLOR_BGR2HSV)
    hair_hs_hist = cv2.calcHist([hsv_hair], [0, 1], None, [16, 16], [0, 180, 0, 256])
    cv2.normalize(hair_hs_hist, hair_hs_hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

    # 2. Full head crop (overall character palette)
    hsv_full = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    full_hs_hist = cv2.calcHist([hsv_full], [0, 1], None, [16, 16], [0, 180, 0, 256])
    cv2.normalize(full_hs_hist, full_hs_hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

    # 3. Structure dHash
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (17, 16))
    dhash = (resized[:, 1:] > resized[:, :-1]).flatten()

    return hair_hs_hist, full_hs_hist, dhash


def is_anime_feature_match(feat1, feat2, tolerance: float = 0.6) -> bool:
    if feat1 is None or feat2 is None:
        return False
    try:
        hair1, full1, dhash1 = feat1
        hair2, full2, dhash2 = feat2

        hair_corr = max(0.0, float(cv2.compareHist(hair1, hair2, cv2.HISTCMP_CORREL)))
        full_corr = max(0.0, float(cv2.compareHist(full1, full2, cv2.HISTCMP_CORREL)))
        dhash_dist = float(np.count_nonzero(dhash1 != dhash2)) / float(len(dhash1))
        dhash_sim = max(0.0, 1.0 - dhash_dist)

        sim = 0.45 * hair_corr + 0.35 * full_corr + 0.20 * dhash_sim

        strictness = float(tolerance) / 0.6
        thresh = 0.48 / max(0.3, strictness)

        if hair_corr >= (0.75 / max(0.4, strictness)):
            return True
        if full_corr >= (0.80 / max(0.4, strictness)):
            return True
        if sim >= thresh:
            return True
        return False
    except Exception:
        return False


class DummyQueue:
    def put(self, *args, **kwargs):
        pass


class TextboxLogHandler(logging.Handler):
    def __init__(self, log_queue=None):
        super().__init__()
        self.log_queue = log_queue if log_queue is not None else DummyQueue()

    def emit(self, record):
        msg = self.format(record)
        self.log_queue.put(("log", msg))


class ScenePackGenerator:
    """
    Backend service for generating video scenepacks.
    """
    def __init__(self, log_queue=None, frame_skip: int = 15, tolerance: float = 0.6, mode: str = "Real Faces"):
        self.log_queue = log_queue if log_queue is not None else DummyQueue()
        self.frame_skip = frame_skip
        self.tolerance = tolerance
        self.mode = mode
        self.is_cancelled = False

        # Determine the directory where the script is located
        if PlatformManager.is_windows():
            self.app_dir = Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / "Focus"
        elif PlatformManager.is_macos():
            self.app_dir = Path(os.path.expanduser('~/Library/Application Support/Focus'))
        else:
            self.app_dir = Path(os.path.expanduser('~/.local/share/Focus'))
        self.app_dir.mkdir(parents=True, exist_ok=True)

        self.anime_cascade_path = self.app_dir / "lbpcascade_animeface.xml"

        self.bin_dir = self.app_dir / "bin"
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        exe_suffix = PlatformManager.get_exe_suffix()
        self.ffmpeg_path = self.bin_dir / f"ffmpeg{exe_suffix}"
        self.ffprobe_path = self.bin_dir / f"ffprobe{exe_suffix}"
        
        if not self.ffmpeg_path.exists() and shutil.which("ffmpeg"):
            self.ffmpeg_path = Path(shutil.which("ffmpeg"))
        if not self.ffprobe_path.exists() and shutil.which("ffprobe"):
            self.ffprobe_path = Path(shutil.which("ffprobe"))
            
        self._active_subprocesses: set[subprocess.Popen] = set()
        self._subproc_lock = threading.Lock()
        self._cached_best_vcodec: Optional[Tuple[str, List[str]]] = None

    def cancel(self):
        self.is_cancelled = True
        self.terminate_all_subprocesses()

    def register_subprocess(self, proc: subprocess.Popen):
        with self._subproc_lock:
            self._active_subprocesses.add(proc)

    def unregister_subprocess(self, proc: subprocess.Popen):
        with self._subproc_lock:
            self._active_subprocesses.discard(proc)

    def terminate_all_subprocesses(self):
        with self._subproc_lock:
            procs = list(self._active_subprocesses)
            self._active_subprocesses.clear()
        for proc in procs:
            if PlatformManager.is_windows():
                try:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
                except Exception:
                    pass
            try:
                proc.terminate()
                proc.wait(timeout=1)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        gc.collect()

    def run_subprocess(self, cmd, **kwargs):
        if "creationflags" not in kwargs and PlatformManager.is_windows():
            kwargs["creationflags"] = PlatformManager.get_creation_flags()
        if kwargs.pop("capture_output", False):
            kwargs["stdout"] = subprocess.PIPE
            kwargs["stderr"] = subprocess.PIPE
        timeout = kwargs.pop("timeout", None)
        try:
            proc = subprocess.Popen(cmd, **kwargs)
        except OSError as e:
            if hasattr(self, 'log_queue') and self.log_queue:
                self.log_queue.put(("log", f"Failed to start subprocess: {e}"))
            is_text = kwargs.get('text', False)
            empty_out = "" if is_text else b""
            err_msg = str(e) if is_text else str(e).encode('utf-8')
            return subprocess.CompletedProcess(cmd, 1, empty_out, err_msg)

        self.register_subprocess(proc)
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            retcode = proc.poll()
            return subprocess.CompletedProcess(cmd, retcode, stdout, stderr)
        except subprocess.TimeoutExpired as e:
            proc.kill()
            stdout, stderr = proc.communicate()
            raise subprocess.TimeoutExpired(cmd, timeout, output=stdout, stderr=stderr) from e
        finally:
            self.unregister_subprocess(proc)

    def _check_and_download_ffmpeg(self):
        if self.ffmpeg_path.exists() and self.ffprobe_path.exists():
            return

        if shutil.which("ffmpeg") and shutil.which("ffprobe"):
            self.ffmpeg_path = Path(shutil.which("ffmpeg"))
            self.ffprobe_path = Path(shutil.which("ffprobe"))
            return

        if not (PlatformManager.is_macos() or PlatformManager.is_windows()):
            self.log_queue.put(("log", "Warning: Auto-download for FFmpeg is currently only supported on macOS and Windows. Please install FFmpeg manually."))
            return

        if PlatformManager.is_windows():
            if not self.ffmpeg_path.exists() or not self.ffprobe_path.exists():
                if self.log_queue:
                    self.log_queue.put(("log", "Downloading FFmpeg for Windows (this may take a minute)..."))
                url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
                zip_path = self.bin_dir / "ffmpeg_win.zip"
                try:
                    urllib.request.urlretrieve(url, zip_path)
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        for file_info in zip_ref.infolist():
                            if file_info.filename.endswith('ffmpeg.exe'):
                                extracted_path = zip_ref.extract(file_info, self.bin_dir)
                                shutil.move(extracted_path, self.ffmpeg_path)
                            elif file_info.filename.endswith('ffprobe.exe'):
                                extracted_path = zip_ref.extract(file_info, self.bin_dir)
                                shutil.move(extracted_path, self.ffprobe_path)
                    
                    # Clean up the extracted folder structure if needed
                    for p in self.bin_dir.iterdir():
                        if p.is_dir() and "ffmpeg" in p.name.lower():
                            shutil.rmtree(p, ignore_errors=True)
                            
                    if self.log_queue:
                        self.log_queue.put(("log", "FFmpeg downloaded successfully."))
                except Exception as e:
                    if self.log_queue:
                        self.log_queue.put(("log", f"Failed to download FFmpeg: {e}"))
                finally:
                    if zip_path.exists():
                        zip_path.unlink()
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
            if PlatformManager.is_macos():
                try:
                    subprocess.run(["xattr", "-d", "com.apple.quarantine", str(self.ffmpeg_path)], capture_output=True)
                except Exception:
                    pass

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
            if PlatformManager.is_macos():
                try:
                    subprocess.run(["xattr", "-d", "com.apple.quarantine", str(self.ffprobe_path)], capture_output=True)
                except Exception:
                    pass

    def _download_anime_cascade(self):
        with CASCADE_DOWNLOAD_LOCK:
            if not self.anime_cascade_path.exists() or self.anime_cascade_path.stat().st_size < 50000:
                self.log_queue.put(("log", "Downloading anime face cascade model..."))
                url = "https://raw.githubusercontent.com/nagadomi/lbpcascade_animeface/master/lbpcascade_animeface.xml"
                try:
                    import ssl
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, context=ctx) as response, open(self.anime_cascade_path, 'wb') as out_file:
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

    def _get_hwaccel_args(self) -> List[str]:
        """Returns optimal input hardware acceleration decoding flags for FFmpeg based on host platform."""
        if PlatformManager.is_windows():
            return ["-hwaccel", "auto"]
        elif PlatformManager.is_macos():
            return ["-hwaccel", "videotoolbox"]
        return []

    def get_audio_tracks(self, video_path: Any) -> List[Tuple[int, str]]:
        """
        Probes input video for available audio streams using ffprobe.
        Returns a list of tuples: (audio_stream_index, track_label).
        """
        tracks = []
        parsed = parse_video_paths(video_path)
        target_path = parsed[0] if parsed else None
        if not target_path or not target_path.exists() or not self.ffprobe_path.exists():
            return [(0, "Default Audio Stream (Track 1)")]

        try:
            cmd = [
                str(self.ffprobe_path), '-v', 'error',
                '-select_streams', 'a',
                '-show_entries', 'stream=index,codec_name:stream_tags=language,title',
                '-of', 'json', str(target_path)
            ]
            res = self.run_subprocess(cmd, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout:
                data = json.loads(res.stdout)
                streams = data.get('streams', [])
                for idx, stream in enumerate(streams):
                    tags = stream.get('tags') or {}
                    lang = tags.get('language', 'und')
                    title = tags.get('title', '')
                    codec = stream.get('codec_name', 'audio')
                    label_parts = [f"Track {idx+1}"]
                    if lang and lang != 'und':
                        label_parts.append(f"[{lang.upper()}]")
                    if title:
                        label_parts.append(f"- {title}")
                    label_parts.append(f"({codec})")
                    tracks.append((idx, " ".join(label_parts)))
        except Exception as e:
            logging.warning(f"Could not probe audio streams with ffprobe: {e}")

        if not tracks:
            tracks = [(0, "Default Audio Stream (Track 1)")]

        return tracks

    def get_video_chapters(self, video_path: Any) -> List[dict]:
        """
        Extracts chapter markers from video file using ffprobe.
        Returns a list of dicts: [{'title': str, 'start': float, 'end': float}]
        """
        chapters = []
        parsed = parse_video_paths(video_path)
        target_path = parsed[0] if parsed else None
        if not target_path or not target_path.exists() or not self.ffprobe_path.exists():
            return []

        try:
            cmd = [
                str(self.ffprobe_path), '-v', 'error',
                '-show_chapters',
                '-of', 'json', str(target_path)
            ]
            res = self.run_subprocess(cmd, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout:
                data = json.loads(res.stdout)
                for chap in data.get('chapters', []):
                    start_time = float(chap.get('start_time', 0.0))
                    end_time = float(chap.get('end_time', 0.0))
                    tags = chap.get('tags') or {}
                    title = tags.get('title') or tags.get('TITLE') or ''
                    chapters.append({
                        'title': title,
                        'start': start_time,
                        'end': end_time
                    })
        except Exception as e:
            logging.warning(f"Could not probe chapters with ffprobe: {e}")
        return chapters

    def detect_intro_outro_ranges(self, video_path: Any, skip_intro: bool = True, skip_outro: bool = False, intro_mode: str = "Auto Chapters", intro_duration: float = 90.0) -> List[Tuple[float, float, str]]:
        """
        Detects intro (OP) and outro (ED) intervals to exclude from scanning.
        Returns a list of tuples: [(start_time, end_time, label), ...]
        """
        if not skip_intro and not skip_outro:
            return []

        excluded = []
        parsed = parse_video_paths(video_path)
        target_path = parsed[0] if parsed else None
        duration = self._get_video_duration(target_path) if target_path else 0.0

        intro_keywords = {'op', 'opening', 'intro', 'ncop', 'theme', 'title song', 'czołówka', 'początek', 'head'}
        outro_keywords = {'ed', 'ending', 'nced', 'outro', 'credits', 'preview', 'tytułowa', 'napisy', 'tail'}

        chapters = self.get_video_chapters(video_path) if target_path else []
        found_chapter_intro = False
        found_chapter_outro = False

        mode_lower = (intro_mode or "").lower()
        use_chapters = "chapter" in mode_lower or "auto" in mode_lower or "rozdział" in mode_lower or mode_lower == ""

        if use_chapters and chapters:
            for chap in chapters:
                title = chap.get('title', '').strip().lower()
                start = float(chap.get('start', 0.0))
                end = float(chap.get('end', 0.0))
                if end <= start:
                    continue

                if skip_intro and any(kw in title for kw in intro_keywords):
                    excluded.append((start, end, f"Intro Chapter '{chap.get('title')}'"))
                    found_chapter_intro = True
                elif skip_outro and any(kw in title for kw in outro_keywords):
                    excluded.append((start, end, f"Outro Chapter '{chap.get('title')}'"))
                    found_chapter_outro = True

        # Fallback if no chapter intro was found or if fixed/custom mode is selected
        if skip_intro and not found_chapter_intro:
            eff_intro_dur = min(float(intro_duration), duration * 0.5) if duration > 0 else float(intro_duration)
            if eff_intro_dur > 0:
                excluded.append((0.0, eff_intro_dur, f"Intro Window (First {int(eff_intro_dur)}s)"))

        if skip_outro and not found_chapter_outro and duration > 120.0:
            eff_outro_dur = min(float(intro_duration), 120.0)
            excluded.append((max(0.0, duration - eff_outro_dur), duration, f"Outro Window (Last {int(eff_outro_dur)}s)"))

        # Sort and merge any overlapping excluded ranges
        excluded.sort(key=lambda x: x[0])
        return excluded

    def filter_excluded_intervals(self, intervals: List[Any], excluded_ranges: List[Tuple[float, float, str]]) -> List[Any]:
        """
        Prunes or trims intervals that overlap with excluded intro/outro ranges.
        """
        if not intervals or not excluded_ranges:
            return intervals

        clean = []
        for item in intervals:
            start = item[0]
            end = item[1]
            avg_x = item[2] if len(item) > 2 else 0.5

            valid_subranges = [(start, end)]
            for ex_s, ex_e, _ in excluded_ranges:
                next_valid = []
                for s, e in valid_subranges:
                    if e <= ex_s or s >= ex_e:
                        next_valid.append((s, e))
                    else:
                        if s < ex_s and (ex_s - s) >= 0.5:
                            next_valid.append((s, ex_s))
                        if e > ex_e and (e - ex_e) >= 0.5:
                            next_valid.append((ex_e, e))
                valid_subranges = next_valid

            for s, e in valid_subranges:
                if e > s + 0.3:
                    clean.append((s, e, avg_x))
        return clean

    def run_startup_benchmark(self) -> dict:
        """Executes a fast hardware benchmark testing CPU throughput and GPU acceleration availability."""
        t_start = time.time()
        cpu_cores = os.cpu_count() or 4
        
        # Test CPU synthetic frame array operation
        dummy_arr = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        for _ in range(5):
            _ = cv2.cvtColor(dummy_arr, cv2.COLOR_BGR2GRAY)
            
        gpu_codec, gpu_args = self._get_best_video_codec_and_args()
        elapsed_ms = int((time.time() - t_start) * 1000)
        
        optimal_threads = min(16, max(4, cpu_cores))
        res = {
            "cpu_cores": cpu_cores,
            "gpu_codec": gpu_codec,
            "benchmark_ms": elapsed_ms,
            "optimal_threads": optimal_threads
        }
        logging.info(f"Hardware Benchmark Complete: {cpu_cores} CPU cores, GPU codec '{gpu_codec}' ({elapsed_ms}ms)")
        return res

    def _get_best_video_codec_and_args(self) -> Tuple[str, List[str]]:
        """Probes FFmpeg for available hardware video encoders and returns the fastest supported codec and its optimal speed arguments."""
        if hasattr(self, "_cached_best_vcodec") and self._cached_best_vcodec is not None:
            return self._cached_best_vcodec

        if PlatformManager.is_macos():
            candidates = [
                ("h264_videotoolbox", []),
                ("hevc_videotoolbox", []),
                ("libx264", ["-preset", "veryfast"])
            ]
        elif PlatformManager.is_windows():
            candidates = [
                ("h264_nvenc", ["-preset", "fast"]),
                ("hevc_nvenc", ["-preset", "fast"]),
                ("h264_amf", []),
                ("hevc_amf", []),
                ("h264_mf", []),
                ("hevc_mf", []),
                ("h264_qsv", ["-preset", "veryfast"]),
                ("hevc_qsv", ["-preset", "veryfast"]),
                ("libx264", ["-preset", "veryfast"])
            ]
        else:
            candidates = [
                ("h264_nvenc", ["-preset", "fast"]),
                ("hevc_nvenc", ["-preset", "fast"]),
                ("h264_amf", []),
                ("h264_vaapi", []),
                ("h264_qsv", ["-preset", "veryfast"]),
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
                res = self.run_subprocess(cmd, capture_output=True, timeout=5)
                if res.returncode == 0:
                    self._cached_best_vcodec = (codec, args)
                    logging.info(f"Hardware acceleration enabled: selected GPU video encoder '{codec}'")
                    return codec, args
            except Exception as e:
                logging.debug(f"Codec probe failed for {codec}: {e}")

        self._cached_best_vcodec = ("libx264", ["-preset", "veryfast"])
        return self._cached_best_vcodec

    def _extract_encodings_list(self, ref_data: Any) -> List[Any]:
        if ref_data is None:
            return []
        if isinstance(ref_data, dict):
            if "encodings" in ref_data and ref_data["encodings"]:
                return ref_data["encodings"]
            elif "encoding" in ref_data and ref_data["encoding"] is not None:
                return [ref_data["encoding"]]
            return []
        if isinstance(ref_data, (list, tuple)):
            return list(ref_data)
        return [ref_data]

    def _extract_anime_features_list(self, ref_data: Any) -> List[Any]:
        if ref_data is None:
            return []
        if isinstance(ref_data, dict):
            if "anime_feature" in ref_data and ref_data["anime_feature"] is not None:
                return [ref_data["anime_feature"]]
            if "features" in ref_data and ref_data["features"]:
                return [f for f in ref_data["features"] if f is not None]
            if "anime_features" in ref_data and ref_data["anime_features"]:
                return [f for f in ref_data["anime_features"] if f is not None]
            if "encoding" in ref_data and isinstance(ref_data["encoding"], (tuple, list)) and len(ref_data["encoding"]) == 3:
                return [ref_data["encoding"]]
            return []
        if isinstance(ref_data, tuple) and len(ref_data) == 3:
            return [ref_data]
        if isinstance(ref_data, list):
            res = []
            for item in ref_data:
                if isinstance(item, tuple) and len(item) == 3:
                    res.append(item)
                elif isinstance(item, dict):
                    res.extend(self._extract_anime_features_list(item))
            return res
        return []

    def load_reference_face(self, ref_image_path: Any):
        if isinstance(ref_image_path, dict) or ref_image_path is None:
            return ref_image_path
            
        path_obj = Path(ref_image_path) if isinstance(ref_image_path, (str, Path)) else ref_image_path
        if hasattr(path_obj, "is_file") and not path_obj.is_file():
            raise FileNotFoundError(f"Reference image not found: {path_obj}")

        logging.info(f"Loading reference face from '{getattr(path_obj, 'name', str(path_obj))}'...")

        if self.mode == "Real Faces":
            image = face_recognition.load_image_file(str(path_obj))
            encodings = safe_face_encodings(image)

            if not encodings:
                err_tmpl = get_translation(self.current_lang, "err_no_human_face")
                if "{name}" in err_tmpl:
                    err_msg = err_tmpl.format(name=getattr(path_obj, 'name', str(path_obj)))
                else:
                    err_msg = err_tmpl
                raise ValueError(err_msg)

            return encodings[0]
        else:
            image_bgr = cv2.imread(str(path_obj))
            if image_bgr is None:
                raise ValueError(f"Could not load reference image: {path_obj}")
            gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
            self._download_anime_cascade()
            anime_cascade = get_cascade_classifier(str(self.anime_cascade_path))
            if anime_cascade is None or (hasattr(anime_cascade, 'empty') and anime_cascade.empty()):
                return None
            
            faces = anime_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(30, 30))
            if len(faces) == 0:
                faces = anime_cascade.detectMultiScale(gray, scaleFactor=1.03, minNeighbors=1, minSize=(20, 20))

            if len(faces) > 0:
                x, y, w, h = faces[0]
                crop_bgr = image_bgr[y:y+h, x:x+w]
            else:
                # Fall back to using the reference image itself (e.g. when user provides a pre-cropped avatar)
                crop_bgr = image_bgr

            features = extract_anime_face_features(crop_bgr)
            return features

    def _get_video_duration(self, video_path: Path) -> float:
        cmd = [
            str(self.ffprobe_path), '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(video_path)
        ]
        result = self.run_subprocess(cmd, capture_output=True, text=True)
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

    def merge_intervals(self, timestamps: List[Any], padding_before: float, padding_after: float, duration: float, max_gap_tolerance: float = 1.5, min_scene_duration: float = 1.0) -> List[Any]:
        if not timestamps:
            return []

        is_tuple_input = False
        norm_ts = []
        for t in timestamps:
            if isinstance(t, (list, tuple)):
                is_tuple_input = True
                norm_ts.append((t[0], t[1] if len(t) > 1 else 0.5))
            else:
                norm_ts.append((float(t), 0.5))

        sorted_ts = sorted([t for t in norm_ts if t[0] >= 0.0], key=lambda x: x[0])
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
            if clip_end > clip_start + 0.05:
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

        final_scenes = []
        for start, end, avg_x in merged:
            scene_dur = end - start
            if scene_dur < min_scene_duration:
                needed = min_scene_duration - scene_dur
                new_end = end + needed
                if duration > 0 and duration != float('inf'):
                    new_end = min(duration, new_end)
                new_dur = new_end - start
                if new_dur < min_scene_duration:
                    start = max(0.0, start - (min_scene_duration - new_dur))
                final_scenes.append((start, new_end, avg_x))
            else:
                final_scenes.append((start, end, avg_x))

        if not final_scenes:
            return []

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

        if not is_tuple_input:
            return [(s, e) for s, e, _ in result]
        return result

    def _detect_silences(self, video_path: Path, buffer_ms: int = 300) -> List[Tuple[float, float]]:
        silences = []
        try:
            d_sec = buffer_ms / 1000.0
            cmd = [
                str(self.ffmpeg_path),
                '-hide_banner', '-loglevel', 'error',
                '-i', str(video_path),
                '-vn', '-sn', '-dn',
                '-af', f'silencedetect=noise=-30dB:d={d_sec}',
                '-f', 'null', '-'
            ]
            result = self.run_subprocess(cmd, capture_output=True, text=True)
            output = result.stderr
            starts = re.findall(r'silence_start:\s*([\d\.]+)', output)
            ends = re.findall(r'silence_end:\s*([\d\.]+)', output)

            for s, e in zip(starts, ends):
                silences.append((float(s), float(e)))
        except Exception as e:
            logging.error(f"VAD Silence Detection failed: {e}")

        return silences

    def _extract_audio_embedding(self, video_path: Path, start_time: float, end_time: float) -> Optional[np.ndarray]:
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                temp_wav_path = temp_wav.name

            dur = end_time - start_time
            if dur <= 0: return None

            cmd = [
                str(self.ffmpeg_path),
                "-y", "-ss", str(start_time), "-t", str(dur),
                "-i", str(video_path),
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                temp_wav_path
            ]
            self.run_subprocess(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            if not os.path.exists(temp_wav_path):
                return None

            with wave.open(temp_wav_path, "rb") as wf:
                rate = wf.getframerate()
                sig = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

            if len(sig) == 0:
                return None

            mfcc_feat = self._compute_numpy_mfcc(sig, rate)
            if mfcc_feat is None or len(mfcc_feat) == 0:
                return None
            return np.mean(mfcc_feat, axis=0)
        except Exception as e:
            logging.error(f"Failed to extract audio embedding: {e}")
            return None
        finally:
            if 'temp_wav_path' in locals() and os.path.exists(temp_wav_path):
                try:
                    os.remove(temp_wav_path)
                except OSError:
                    pass

    @staticmethod
    def _compute_numpy_mfcc(sig: np.ndarray, rate: int = 16000, num_cep: int = 13, nfft: int = 512) -> Optional[np.ndarray]:
        """Pure NumPy implementation of MFCC feature extraction (zero SciPy / C-extension dependencies)."""
        try:
            sig = sig.astype(np.float64)
            emphasized = np.append(sig[0], sig[1:] - 0.97 * sig[:-1])
            frame_len = int(round(0.025 * rate))
            frame_step = int(round(0.010 * rate))
            sig_len = len(emphasized)
            if sig_len < frame_len:
                return None
            num_frames = int(np.ceil(float(np.abs(sig_len - frame_len)) / frame_step)) + 1
            pad_len = (num_frames - 1) * frame_step + frame_len
            pad_sig = np.append(emphasized, np.zeros((pad_len - sig_len)))
            indices = np.tile(np.arange(0, frame_len), (num_frames, 1)) + np.tile(np.arange(0, num_frames * frame_step, frame_step), (frame_len, 1)).T
            frames = pad_sig[indices.astype(np.int32, copy=False)]
            frames *= np.hamming(frame_len)
            mag_frames = np.absolute(np.fft.rfft(frames, nfft))
            pow_frames = (1.0 / nfft) * (mag_frames ** 2)
            nfilt = 26
            low_mel = 0
            high_mel = 2595 * np.log10(1 + (rate / 2) / 700)
            mel_points = np.linspace(low_mel, high_mel, nfilt + 2)
            hz_points = 700 * (10**(mel_points / 2595) - 1)
            bin_idx = np.floor((nfft + 1) * hz_points / rate)
            fbank = np.zeros((nfilt, int(np.floor(nfft / 2 + 1))))
            for m in range(1, nfilt + 1):
                f_m_minus = int(bin_idx[m - 1])
                f_m = int(bin_idx[m])
                f_m_plus = int(bin_idx[m + 1])
                for k in range(f_m_minus, f_m):
                    fbank[m - 1, k] = (k - bin_idx[m - 1]) / max(1e-5, (bin_idx[m] - bin_idx[m - 1]))
                for k in range(f_m, f_m_plus):
                    fbank[m - 1, k] = (bin_idx[m + 1] - k) / max(1e-5, (bin_idx[m + 1] - bin_idx[m]))
            feat = np.dot(pow_frames, fbank.T)
            feat = np.where(feat == 0, np.finfo(float).eps, feat)
            feat = 20 * np.log10(feat)
            n_feat = feat.shape[1]
            n_arr = np.arange(n_feat)
            k_arr = np.arange(num_cep)[:, None]
            dct_m = np.cos(np.pi / n_feat * (n_arr + 0.5) * k_arr)
            mfcc = np.dot(feat, dct_m.T)
            return mfcc
        except Exception:
            return None

    def _build_target_voice_print(self, video_path: Path, intervals: List[Tuple[float, float, float]]) -> Optional[np.ndarray]:
        sorted_intervals = sorted(intervals, key=lambda x: x[1] - x[0], reverse=True)
        embeddings = []
        for s, e, _ in sorted_intervals[:3]:
            dur = e - s
            if dur < 0.5:
                continue
            test_s = s + (dur / 2) - min(1.0, dur / 2)
            test_e = test_s + min(2.0, dur)
            emb = self._extract_audio_embedding(video_path, test_s, test_e)
            if emb is not None:
                embeddings.append(emb)

        if len(embeddings) > 0:
            return np.mean(embeddings, axis=0)
        return None

    def _check_lip_movement(self, video_path: Path, timestamp: float, target_encoding: np.ndarray, duration_sec: float = 0.5) -> bool:
        if self.mode != "Real Faces" or target_encoding is None:
            return True

        cap = cv2.VideoCapture(str(video_path))
        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 24

            cap.set(cv2.CAP_PROP_POS_MSEC, max(0, timestamp) * 1000)
            frames_to_check = max(5, int(duration_sec * fps))
            mouth_distances = []

            for _ in range(frames_to_check):
                ret, frame = cap.read()
                if not ret:
                    break

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_locations = safe_face_locations(rgb_frame, model="hog")
                if not face_locations:
                    continue

                encodings = safe_face_encodings(rgb_frame, face_locations)
                ref_encs = self._extract_encodings_list(target_encoding)
                for loc, enc in zip(face_locations, encodings):
                    if ref_encs:
                        matches = safe_compare_faces(ref_encs, enc, tolerance=0.5)
                        match = any(matches)
                    else:
                        match = True

                    if match:
                        landmarks = safe_face_landmarks(rgb_frame, [loc])
                        if landmarks and 'top_lip' in landmarks[0] and 'bottom_lip' in landmarks[0]:
                            top_lip = landmarks[0]['top_lip']
                            bottom_lip = landmarks[0]['bottom_lip']
                            top_y = sum([p[1] for p in top_lip]) / len(top_lip)
                            bottom_y = sum([p[1] for p in bottom_lip]) / len(bottom_lip)
                            mouth_distances.append(abs(bottom_y - top_y))
                        break
        finally:
            cap.release()

        if len(mouth_distances) > 2:
            variance = np.var(mouth_distances)
            return variance > 1.5

        return False

    def find_scenes(self, video_path: Path, ref_data, padding_before: float, padding_after: float, max_gap_tolerance: float = 1.5, min_scene_duration: float = 1.0, video_index: int = 0, total_videos: int = 1, skip_intro: bool = False, skip_outro: bool = False, intro_mode: str = "Auto Chapters", intro_duration: float = 90.0) -> List[Tuple[float, float, float]]:
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

            timestamps = []

            # Detect intro/outro ranges to exclude
            excluded_ranges = self.detect_intro_outro_ranges(
                video_path, skip_intro=skip_intro, skip_outro=skip_outro,
                intro_mode=intro_mode, intro_duration=intro_duration
            )
            if excluded_ranges:
                for ex_s, ex_e, ex_lbl in excluded_ranges:
                    msg = f"[{video_path.name}] Skipping {ex_lbl} [{ex_s:.1f}s -> {ex_e:.1f}s]"
                    logging.info(msg)
                    if hasattr(self, "log_queue") and self.log_queue:
                        self.log_queue.put(("log", msg))

            cascade = None
            profile_cascade = None
            if self.mode == "Anime":
                self.log_queue.put(("log", "Note: Anime mode detects all faces in the frame, not a specific character."))
                self._download_anime_cascade()
                cascade = get_cascade_classifier(str(self.anime_cascade_path))
                if cascade is None or (hasattr(cascade, 'empty') and cascade.empty()):
                    self.log_queue.put(("log", "Notice: Anime Haar cascade classifier unavailable. Falling back to neural face recognition model."))
            elif self.mode == "Real Faces":
                if hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
                    profile_cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_profileface.xml')  # type: ignore[attr-defined]
                    profile_cascade = get_cascade_classifier(profile_cascade_path)

            logging.info(f"Starting high-speed multi-core facial recognition scan in {self.mode} mode...")
            start_time = time.time()

            ref_encs_list = self._extract_encodings_list(ref_data)
            ref_anime_feats = self._extract_anime_features_list(ref_data)

            raw_target_indices = list(range(0, total_frames, max(1, self.frame_skip)))
            if excluded_ranges:
                target_indices = [
                    idx for idx in raw_target_indices
                    if not any(ex_s <= (idx / fps) <= ex_e for ex_s, ex_e, _ in excluded_ranges)
                ]
            else:
                target_indices = raw_target_indices
            total_targets = len(target_indices)

            thread_local_data = threading.local()

            def _process_single_frame(item):
                target_idx, frame = item
                if frame is None or frame.size == 0:
                    return None

                h, w = frame.shape[:2]
                target_w = 640 if self.mode == "Anime" else 480
                if w > target_w:
                    ratio = float(target_w) / float(w)
                    new_h = int(h * ratio)
                    small_frame = cv2.resize(frame, (target_w, new_h))
                else:
                    small_frame = frame

                w_resized = small_frame.shape[1]

                if self.mode == "Real Faces":
                    rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                    face_locations = safe_face_locations(rgb_frame, model="hog")

                    if not hasattr(thread_local_data, 'profile_cascade'):
                        if hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
                            p_path = os.path.join(cv2.data.haarcascades, 'haarcascade_profileface.xml')
                            thread_local_data.profile_cascade = get_cascade_classifier(p_path)
                        else:
                            thread_local_data.profile_cascade = None
                            
                    local_profile_cascade = thread_local_data.profile_cascade

                    if not face_locations and local_profile_cascade and hasattr(local_profile_cascade, 'empty') and not local_profile_cascade.empty():
                        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)

                        profiles_right = local_profile_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                        for (x, y, w_box, h_box) in profiles_right:
                            face_locations.append((y, x+w_box, y+h_box, x))

                        flipped_gray = cv2.flip(gray, 1)
                        profiles_left = local_profile_cascade.detectMultiScale(flipped_gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                        h_img, w_img = gray.shape
                        for (x, y, w_box, h_box) in profiles_left:
                            x_real = w_img - (x + w_box)
                            face_locations.append((y, x_real+w_box, y+h_box, x_real))

                    if face_locations:
                        face_encodings = safe_face_encodings(rgb_frame, face_locations)

                        for idx_enc, encoding in enumerate(face_encodings):
                            if ref_encs_list:
                                matches = safe_compare_faces(ref_encs_list, encoding, tolerance=self.tolerance)
                                if any(matches):
                                    top, right, bottom, left = face_locations[idx_enc]
                                    center_x = (left + right) / 2.0
                                    rel_x = center_x / w_resized
                                    return (target_idx / fps, rel_x)
                            else:
                                top, right, bottom, left = face_locations[idx_enc]
                                center_x = (left + right) / 2.0
                                rel_x = center_x / w_resized
                                return (target_idx / fps, rel_x)

                elif self.mode == "Anime":
                    if not hasattr(thread_local_data, 'anime_cascade'):
                        thread_local_data.anime_cascade = get_cascade_classifier(str(self.anime_cascade_path))
                        
                    local_anime_cascade = thread_local_data.anime_cascade
                    
                    if local_anime_cascade is not None and hasattr(local_anime_cascade, 'empty') and not local_anime_cascade.empty():
                        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                        faces = local_anime_cascade.detectMultiScale(gray, scaleFactor=1.06, minNeighbors=3, minSize=(16, 16))
                        if len(faces) == 0:
                            faces = local_anime_cascade.detectMultiScale(gray, scaleFactor=1.04, minNeighbors=2, minSize=(14, 14))

                        if len(faces) > 0:
                            if ref_anime_feats:
                                for (x_f, y_f, w_f, h_f) in faces:
                                    crop_bgr = small_frame[y_f:y_f+h_f, x_f:x_f+w_f]
                                    if crop_bgr.size > 0:
                                        curr_feat = extract_anime_face_features(crop_bgr)
                                        if any(is_anime_feature_match(ref_f, curr_feat, tolerance=self.tolerance) for ref_f in ref_anime_feats):
                                            center_x = x_f + w_f / 2.0
                                            rel_x = center_x / w_resized
                                            return (target_idx / fps, rel_x)
                            else:
                                (x_f, y_f, w_f, h_f) = faces[0]
                                center_x = x_f + w_f / 2.0
                                rel_x = center_x / w_resized
                                return (target_idx / fps, rel_x)
                    else:
                        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                        if not hasattr(thread_local_data, 'face_cascade'):
                            if hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
                                p_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
                                thread_local_data.face_cascade = get_cascade_classifier(p_path)
                            else:
                                thread_local_data.face_cascade = None
                        local_face_cascade = thread_local_data.face_cascade
                        if local_face_cascade and not local_face_cascade.empty():
                            faces = local_face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                            if len(faces) > 0:
                                if ref_anime_feats:
                                    for (x_f, y_f, w_f, h_f) in faces:
                                        crop_bgr = small_frame[y_f:y_f+h_f, x_f:x_f+w_f]
                                        if crop_bgr.size > 0:
                                            curr_feat = extract_anime_face_features(crop_bgr)
                                            if any(is_anime_feature_match(ref_f, curr_feat, tolerance=self.tolerance) for ref_f in ref_anime_feats):
                                                rel_x = (x_f + w_f / 2.0) / w_resized
                                                return (target_idx / fps, rel_x)
                                else:
                                    (x_f, y_f, w_f, h_f) = faces[0]
                                    rel_x = (x_f + w_f / 2.0) / w_resized
                                    return (target_idx / fps, rel_x)

                return None

            batch_size = 32
            max_workers = min(4, os.cpu_count() or 4)

            current_idx = 0
            target_idx_set = set(target_indices)
            
            while current_idx < total_frames:
                if getattr(self, 'is_cancelled', False):
                    logging.info("Scene extraction cancelled by user.")
                    break

                batch_frames = []
                while len(batch_frames) < batch_size and current_idx < total_frames:
                    ret = cap.grab()
                    if not ret:
                        current_idx = total_frames
                        break
                    
                    if current_idx in target_idx_set:
                        ret_ret, frame = cap.retrieve()
                        if ret_ret and frame is not None:
                            batch_frames.append((current_idx, frame))
                    current_idx += 1

                if not batch_frames:
                    continue

                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    results = list(executor.map(_process_single_frame, batch_frames))

                for res in results:
                    if res is not None:
                        timestamps.append(res)

                current_frame = batch_frames[-1][0]
                episode_progress = min(1.0, current_frame / total_frames)
                composite_progress = (video_index + episode_progress) / float(total_videos)
                elapsed = time.time() - start_time
                eta_seconds = (elapsed / episode_progress) - elapsed if episode_progress > 0 else 0

                eta_mins = int(eta_seconds // 60)
                eta_secs = int(eta_seconds % 60)

                if total_videos > 1:
                    status_text = f"Episode [{video_index + 1}/{total_videos}] '{video_path.name}' ({int(episode_progress*100)}%) | Overall: {int(composite_progress*100)}% | ETA: {eta_mins}m {eta_secs}s"
                    if hasattr(self, "log_queue") and self.log_queue:
                        self.log_queue.put(("episode_progress", (video_index + 1, total_videos, video_path.name, episode_progress, composite_progress)))
                else:
                    status_text = f"ETA: {eta_mins}m {eta_secs}s  ({int(episode_progress*100)}%)"

                if hasattr(self, "log_queue") and self.log_queue:
                    self.log_queue.put(("progress", composite_progress, status_text))

                if len(timestamps) % (batch_size * 2) < batch_size:
                    logging.info(f"[{video_path.name}] Scanned {min(current_frame, total_frames)}/{total_frames} frames ({int(episode_progress*100)}%)...")
                    gc.collect()

        finally:
            cap.release()
            gc.collect()

        self.log_queue.put(("progress", 1.0, "Scan Complete"))

        duration = self._get_video_duration(video_path)
        merged_intervals = self.merge_intervals(timestamps, padding_before, padding_after, duration, max_gap_tolerance, min_scene_duration)

        if excluded_ranges:
            merged_intervals = self.filter_excluded_intervals(merged_intervals, excluded_ranges)

        return merged_intervals

    def get_video_bitrate(self, video_path: Union[str, Path]) -> int:
        """Returns the source video bitrate in bits per second (bps) with caching."""
        v_path = Path(video_path)
        if not v_path.exists():
            return 3_000_000

        if not hasattr(self, "_cached_bitrates"):
            self._cached_bitrates = {}
        if str(v_path) in self._cached_bitrates:
            return self._cached_bitrates[str(v_path)]

        cmd = [
            str(self.ffprobe_path), '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=bit_rate',
            '-show_entries', 'format=bit_rate,duration,size',
            '-of', 'json',
            str(v_path)
        ]
        try:
            res = self.run_subprocess(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                streams = data.get("streams", [])
                if streams and streams[0].get("bit_rate"):
                    val = int(streams[0]["bit_rate"])
                    if val > 100_000:
                        self._cached_bitrates[str(v_path)] = val
                        return val

                format_info = data.get("format", {})
                if format_info.get("bit_rate"):
                    val = int(format_info["bit_rate"])
                    if val > 100_000:
                        self._cached_bitrates[str(v_path)] = val
                        return val

                size = float(format_info.get("size", 0))
                duration = float(format_info.get("duration", 0))
                if size > 0 and duration > 0:
                    calc_bps = int((size * 8) / duration)
                    if calc_bps > 100_000:
                        self._cached_bitrates[str(v_path)] = calc_bps
                        return calc_bps
        except Exception as e:
            logging.debug(f"Failed to probe bitrate for {v_path}: {e}")

        self._cached_bitrates[str(v_path)] = 3_000_000
        return 3_000_000

    def extract_and_concat(self, video_path: Path, intervals: List[Tuple[float, float, float]], output_path: Path, aspect_ratio: str = "16:9 Original", audio_track_index: int = 0, export_quality: str = "Auto (Match Source Bitrate)"):
        if not intervals:
            logging.warning("No scenes to extract.")
            return

        temp_dir = Path(tempfile.mkdtemp(prefix="scenepack_tmp_"))
        concat_list_path = temp_dir / "concat_list.txt"

        try:
            codec, extra_args = self._get_best_video_codec_and_args()
            logging.info(f"Extracting scenes in parallel via FFmpeg (codec: {codec}, audio track: {audio_track_index})...")
            if hasattr(self, "log_queue") and self.log_queue:
                self.log_queue.put(("log", f"Rendering with Hardware Acceleration: using video encoder '{codec}' (audio track: {audio_track_index + 1})."))

            total_segments = len(intervals)
            completed_count = 0
            count_lock = threading.Lock()

            def process_segment(index_and_interval):
                nonlocal completed_count
                i, interval = index_and_interval
                if len(interval) >= 4 and isinstance(interval[0], (str, Path)):
                    src_video = Path(interval[0])
                    start = float(interval[1])
                    end = float(interval[2])
                    avg_x = float(interval[3])
                else:
                    src_video = Path(video_path) if video_path else Path(interval[0])
                    start = float(interval[0])
                    end = float(interval[1])
                    avg_x = float(interval[2]) if len(interval) > 2 else 0.5

                chunk_path = temp_dir / f"chunk_{i:04d}.ts"
                duration = end - start

                vf_filter = "setpts=PTS-STARTPTS,fps=24"
                aspect_lower = aspect_ratio.lower()
                if "9:16" in aspect_ratio and ("vert" in aspect_lower or "auto" in aspect_lower or "pion" in aspect_lower or "vertical" in aspect_lower):
                    vf_filter = f"crop='ceil(ih*9/32)*2':'ceil(ih/2)*2':'max(0,min(iw-ceil(ih*9/32)*2,floor(iw*{avg_x}-ceil(ih*9/32))))':0,setpts=PTS-STARTPTS,fps=24"
                elif "9:16" in aspect_ratio and ("blur" in aspect_lower or "rozm" in aspect_lower or "tł" in aspect_lower or "background" in aspect_lower):
                    vf_filter = "[0:v]split=2[fg][bg];[bg]scale='ceil(ih*9/32)*2':'ceil(ih/2)*2':force_original_aspect_ratio=increase,crop='ceil(ih*9/32)*2':'ceil(ih/2)*2',boxblur=20:20[bg2];[fg]scale='ceil(ih*9/32)*2':'ceil(ih/2)*2':force_original_aspect_ratio=decrease[fg2];[bg2][fg2]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2,setpts=PTS-STARTPTS,fps=24"

                hwaccel_flags = self._get_hwaccel_args()
                cmd = [
                    str(self.ffmpeg_path), '-y',
                    '-hide_banner', '-loglevel', 'error'
                ] + hwaccel_flags + [
                    '-ss', str(start),
                    '-accurate_seek',
                    '-i', str(src_video),
                    '-t', str(duration),
                    '-fps_mode', 'cfr'
                ]

                if "blur" in aspect_lower or "rozm" in aspect_lower or "background" in aspect_lower:
                    cmd.extend(['-filter_complex', vf_filter])
                else:
                    cmd.extend(['-vf', vf_filter])

                quality_str = export_quality.lower()
                is_auto_source = "auto" in quality_str or "source" in quality_str or "źródł" in quality_str or "dopasuj" in quality_str or "match" in quality_str

                if is_auto_source:
                    src_bps = self.get_video_bitrate(src_video)
                    # Add 15% safety headroom so re-encoding maintains visual fidelity without file size bloating
                    target_bps = max(1_200_000, min(35_000_000, int(src_bps * 1.15)))
                    b_val = f"{int(target_bps / 1000)}k"
                    maxrate_val = f"{int(target_bps * 1.5 / 1000)}k"
                    buf_val = f"{int(target_bps * 2.0 / 1000)}k"
                    crf_val = '18'
                    q_val = None
                elif "max" in quality_str or "master" in quality_str:
                    crf_val = '14'
                    q_val = '85'
                    b_val = '35M'
                    maxrate_val = '50M'
                    buf_val = '70M'
                elif "high" in quality_str or "wysoka" in quality_str or "16" in quality_str or "17" in quality_str or "20" in quality_str:
                    crf_val = '17'
                    q_val = '72'
                    b_val = '20M'
                    maxrate_val = '28M'
                    buf_val = '40M'
                elif "low" in quality_str or "draft" in quality_str or "szkic" in quality_str or "24" in quality_str or "4" in quality_str:
                    crf_val = '24'
                    q_val = '42'
                    b_val = '4M'
                    maxrate_val = '6M'
                    buf_val = '8M'
                else: # Medium / Standard
                    crf_val = '20'
                    q_val = '58'
                    b_val = '10M'
                    maxrate_val = '15M'
                    buf_val = '20M'

                if codec == 'libx264':
                    rate_control_args = ['-crf', crf_val, '-maxrate', maxrate_val, '-bufsize', buf_val] if is_auto_source else ['-crf', crf_val]
                elif 'videotoolbox' in codec:
                    if q_val is not None and not is_auto_source:
                        rate_control_args = ['-q:v', q_val, '-b:v', b_val, '-maxrate', maxrate_val, '-bufsize', buf_val]
                    else:
                        rate_control_args = ['-b:v', b_val, '-maxrate', maxrate_val, '-bufsize', buf_val]
                elif 'nvenc' in codec or 'qsv' in codec:
                    if not is_auto_source and q_val is not None:
                        rate_control_args = ['-cq', crf_val, '-b:v', b_val, '-maxrate', maxrate_val, '-bufsize', buf_val]
                    else:
                        rate_control_args = ['-b:v', b_val, '-maxrate', maxrate_val, '-bufsize', buf_val]
                else:
                    rate_control_args = ['-b:v', b_val, '-maxrate', maxrate_val, '-bufsize', buf_val]
                cmd.extend([
                    '-map', '0:v:0',
                    '-map', f'0:a:{audio_track_index}?',
                    '-af', 'aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,aresample=async=1,apad',
                    '-c:v', codec,
                ] + extra_args + rate_control_args + [
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

                result = self.run_subprocess(cmd, capture_output=True, text=True)
                if getattr(self, 'is_cancelled', False):
                    return i, None
                if result.returncode != 0 and hwaccel_flags:
                    # Retry without hwaccel flags if hardware decoding fails for specific container/codecs
                    cmd_fallback = [
                        str(self.ffmpeg_path), '-y',
                        '-hide_banner', '-loglevel', 'error',
                        '-ss', str(start),
                        '-accurate_seek',
                        '-i', str(src_video),
                        '-t', str(duration),
                        '-fps_mode', 'cfr'
                    ]
                    if "blur" in aspect_lower or "rozm" in aspect_lower or "background" in aspect_lower:
                        cmd_fallback.extend(['-filter_complex', vf_filter])
                    else:
                        cmd_fallback.extend(['-vf', vf_filter])
                    cmd_fallback.extend(cmd[cmd.index('-af'):])
                    result = self.run_subprocess(cmd_fallback, capture_output=True, text=True)

                if result.returncode != 0:
                    logging.error(f"FFmpeg slice failed for segment {i+1}: {result.stderr}")
                    return i, None

                with count_lock:
                    completed_count += 1
                    render_prog = completed_count / float(total_segments)
                    if hasattr(self, "log_queue") and self.log_queue:
                        self.log_queue.put(("progress", render_prog, f"Rendering clips: {completed_count}/{total_segments} ({int(render_prog*100)}%)"))
                    if completed_count % max(1, total_segments // 10) == 0 or completed_count == total_segments:
                        logging.info(f"Completed {completed_count}/{total_segments} segments...")

                return i, chunk_path

            max_workers = min(6, os.cpu_count() or 4)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(process_segment, enumerate(intervals)))

            results.sort(key=lambda x: x[0])

            chunk_paths = [cp for _, cp in results if cp and cp.exists()]
            write_concat_list(chunk_paths, concat_list_path)

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

            concat_result = self.run_subprocess(concat_cmd, cwd=temp_dir, capture_output=True, text=True)
            if concat_result.returncode != 0:
                raise RuntimeError(f"FFmpeg concat failed: {concat_result.stderr}")

            logging.info(f"Successfully saved scenepack to:\n{output_path.name}")

        finally:
            logging.info("Cleaning up temporary chunk files...")
            shutil.rmtree(temp_dir, ignore_errors=True)
            gc.collect()

    def _detect_scene_cuts(self, video_path: Path, threshold: float = 0.3) -> List[float]:
        cuts = []
        try:
            cmd = [
                str(self.ffmpeg_path),
                '-hide_banner', '-loglevel', 'error',
                '-i', str(video_path),
                '-an', '-sn', '-dn',
                '-vf', f"scale=320:-1,select='gt(scene,{threshold})',showinfo",
                '-f', 'null', '-'
            ]
            result = self.run_subprocess(cmd, capture_output=True, text=True)
            output = result.stderr
            pts_times = re.findall(r'pts_time:\s*([\d\.]+)', output)
            cuts = [float(pt) for pt in pts_times]
        except Exception as e:
            logging.error(f"Scene cut detection failed: {e}")
        return cuts

    def scan_and_prepare(self, video_path: Any, ref_image_path: Any, padding_before: float = 2.0, padding_after: float = 2.0, max_gap_tolerance: float = 1.5, min_scene_duration: float = 1.0, vad_enabled: bool = False, vad_buffer: int = 300, vad_speaker_enabled: bool = True, vad_speaker_threshold: float = 0.68, skip_intro: bool = False, skip_outro: bool = False, intro_mode: str = "Auto Chapters", intro_duration: float = 90.0) -> List[Any]:
        self._check_and_download_ffmpeg()

        video_paths = parse_video_paths(video_path)
        if not video_paths:
            raise FileNotFoundError(f"No valid video file(s) provided: {video_path}")

        if isinstance(ref_image_path, dict):
            ref_data = ref_image_path
        else:
            ref_data = self.load_reference_face(ref_image_path)

        all_intervals = []
        total_videos = len(video_paths)
        for idx, v_path in enumerate(video_paths):
            if not v_path.is_file():
                logging.warning(f"Video file not found: {v_path}, skipping.")
                continue

            if total_videos > 1:
                msg = f"Scanning input video {idx + 1}/{total_videos}: '{v_path.name}'..."
                logging.info(msg)
                if hasattr(self, "log_queue") and self.log_queue:
                    self.log_queue.put(("log", msg))
                    self.log_queue.put(("progress", idx / float(total_videos), msg))

            intervals = self.find_scenes(
                v_path, ref_data, padding_before, padding_after, max_gap_tolerance, min_scene_duration,
                video_index=idx, total_videos=total_videos,
                skip_intro=skip_intro, skip_outro=skip_outro,
                intro_mode=intro_mode, intro_duration=intro_duration
            )

            logging.info(f"[{v_path.name}] Detecting shot boundaries for scene snapping...")
            scene_cuts = self._detect_scene_cuts(v_path)

            if vad_enabled:
                logging.info(f"[{v_path.name}] VAD Protection Enabled. Running FFmpeg silence detection...")
                silences = self._detect_silences(v_path, vad_buffer)
                if silences:
                    logging.info(f"[{v_path.name}] Detected {len(silences)} silence intervals. Snapping boundaries...")
                    refined_intervals = []
                    for item in intervals:
                        start, end = item[0], item[1]
                        avg_x = item[2] if len(item) > 2 else 0.5
                        new_start, new_end = start, end

                        # Forward boundary: Max extension capped at 2.5s and strictly bounded by the nearest scene cut
                        subsequent_cuts = [c for c in scene_cuts if c > end]
                        nearest_cut_end = subsequent_cuts[0] if subsequent_cuts else (end + 2.5)
                        max_allowed_end = min(end + 2.5, nearest_cut_end)

                        if not any(s <= end <= e for s, e in silences):
                            next_silences = [s for s, e in silences if s >= end]
                            if next_silences:
                                candidate_end = next_silences[0]
                                if candidate_end <= max_allowed_end:
                                    is_speaking = self._check_lip_movement(v_path, end - 0.2, ref_data)
                                    if is_speaking:
                                        logging.info(f"Lip-Sync: Extending {end:.2f}s to {candidate_end:.2f}s.")
                                        new_end = candidate_end
                                elif subsequent_cuts and abs(subsequent_cuts[0] - end) <= 0.8:
                                    new_end = subsequent_cuts[0]

                        # Backward boundary: Max pullback capped at 2.5s and strictly bounded by the prior scene cut
                        prior_cuts = [c for c in scene_cuts if c < start]
                        nearest_cut_start = prior_cuts[-1] if prior_cuts else 0.0
                        min_allowed_start = max(0.0, start - 2.5, nearest_cut_start)

                        if not any(s <= start <= e for s, e in silences):
                            prev_silences = [e for s, e in silences if e <= start]
                            if prev_silences:
                                candidate_start = prev_silences[-1]
                                if candidate_start >= min_allowed_start:
                                    is_speaking_start = self._check_lip_movement(v_path, start, ref_data)
                                    if is_speaking_start:
                                        logging.info(f"Lip-Sync: Pulling {start:.2f}s back to {candidate_start:.2f}s.")
                                        new_start = candidate_start
                                elif prior_cuts and abs(start - prior_cuts[-1]) <= 0.8:
                                    new_start = prior_cuts[-1]

                        refined_intervals.append((max(0.0, new_start), new_end, avg_x))

                    final_intervals: List[Tuple[float, float, float]] = []
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

                    if vad_speaker_enabled and len(intervals) > 0:
                        logging.info(f"[{v_path.name}] Target Speaker Voice Matching Enabled. Enrolling Target Voice Print...")
                        voice_print = self._build_target_voice_print(v_path, intervals)
                        if voice_print is not None:
                            logging.info(f"[{v_path.name}] Target Voice Enrolled. Verifying speakers across {len(intervals)} clips...")
                            verified_intervals = []
                            for item in intervals:
                                s, e = item[0], item[1]
                                avg_x = item[2] if len(item) > 2 else 0.5
                                dur = e - s
                                if dur < 0.2:
                                    continue
                                test_s = s + (dur / 2) - min(1.0, dur / 2)
                                test_e = test_s + min(2.0, dur)
                                emb = self._extract_audio_embedding(v_path, test_s, test_e)
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
                                    verified_intervals.append((s, e, avg_x))
                            intervals = verified_intervals
                        else:
                            logging.warning(f"[{v_path.name}] Failed to build Target Voice Print. Skipping speaker verification.")

            snapped_intervals = []
            for item in intervals:
                start, end = item[0], item[1]
                avg_x = item[2] if len(item) > 2 else 0.5
                new_start, new_end = start, end
                nearest_start_cut = next((c for c in scene_cuts if abs(c - start) <= 0.8), None)
                if nearest_start_cut is not None:
                    new_start = nearest_start_cut

                nearest_end_cut = next((c for c in scene_cuts if abs(c - end) <= 0.8), None)
                if nearest_end_cut is not None:
                    new_end = nearest_end_cut

                if new_end > new_start + 0.1:
                    snapped_intervals.append((new_start, new_end, avg_x))
            intervals = snapped_intervals

            for item in intervals:
                start, end = item[0], item[1]
                avg_x = item[2] if len(item) > 2 else 0.5
                if total_videos > 1:
                    all_intervals.append((str(v_path), start, end, avg_x))
                else:
                    all_intervals.append((start, end, avg_x))

        if not all_intervals:
            raise ValueError("Target face was not detected in any of the input videos.")

        return all_intervals

    def generate(self, video_path: Path, ref_image_path: Path, output_path: Path, padding_before: float = 2.0, padding_after: float = 2.0, max_gap_tolerance: float = 1.5, min_scene_duration: float = 1.0, export_quality: str = "Medium"):
        """
        Main pipeline method to generate a scenepack (CLI compatibility wrapper).
        """
        try:
            intervals = self.scan_and_prepare(
                video_path=video_path,
                ref_image_path=ref_image_path,
                padding_before=padding_before,
                padding_after=padding_after,
                max_gap_tolerance=max_gap_tolerance,
                min_scene_duration=min_scene_duration
            )
        except ValueError as e:
            logging.warning(str(e))
            self.log_queue.put(("log", str(e)))
            return

        if not intervals:
            logging.warning("Target face was not detected in the video. Aborting.")
            self.log_queue.put(("log", "Target face was not detected in the video. Aborting."))
            return

        self.extract_and_concat(
            video_path=video_path,
            intervals=intervals,
            output_path=output_path,
            export_quality=export_quality
        )
