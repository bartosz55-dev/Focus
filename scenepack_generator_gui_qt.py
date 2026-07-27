import os
import sys
import json
import logging
import tempfile
from pathlib import Path
from typing import List, Tuple, Any, Optional

# macOS specific GUI fixes to prevent Cocoa/Qt/OpenCV collisions and window hiding
if sys.platform == "darwin":
    os.environ["QT_MAC_WANTS_LAYER"] = "1"
    os.environ["OPENCV_UI_BACKEND"] = "none"

import cv2
import numpy as np
from PIL import Image

from PySide6.QtCore import Qt, QSize, QUrl, QTimer, Slot
from PySide6.QtGui import QIcon, QFont, QColor, QPalette, QPixmap, QImage, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QCheckBox, QSlider, QProgressBar, QComboBox,
    QScrollArea, QTabWidget, QFrame, QMessageBox, QFileDialog, QTextEdit,
    QSplitter, QStackedWidget, QButtonGroup, QRadioButton, QAbstractItemView,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QDialog
)

# Import shared backend engine and helpers from scenepack_generator_backend
import scenepack_generator_backend as sg_engine
from scenepack_generator_backend import (
    ScenePackGenerator, get_translation, TRANSLATIONS, canonicalize_mode,
    make_square_crop, extract_anime_face_features, is_anime_feature_match, APP_VERSION
)
from scenepack_generator_workers_qt import (
    QtLogHandler, QtQueueProxy, ScanWorker, RenderWorker, GalleryScanWorker
)

class ModernCard(QFrame):
    """Rounded container frame with border styling for grouping UI elements."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ModernCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

class FocusApp(QMainWindow):
    """
    Main Application Window in PySide6 (Qt 6).
    Replaces CustomTkinter with a high-performance, responsive Modern Dark Studio UI.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Focus - AI Scenepack Generator ({APP_VERSION})")
        self.resize(1150, 780)
        self.setMinimumSize(950, 650)

        # State and settings
        self.settings = self.load_settings()
        self.current_theme = self.settings.get("theme", "blue")
        self.current_lang = self.settings.get("language", "English")
        self.current_mode = self.settings.get("default_mode", "Real Faces")
        
        # Selected data
        self.video_path_str = ""
        self.image_path_str = ""
        self.output_path_str = ""
        self.selected_ref_data = None
        self.scanned_intervals: List[Tuple[float, float, float]] = []
        self.review_checkboxes: List[Tuple[Tuple[float, float, float], QCheckBox]] = []

        # Threading workers
        self.queue_proxy = QtQueueProxy()
        self._setup_proxy_connections()
        self.scan_worker: Optional[ScanWorker] = None
        self.render_worker: Optional[RenderWorker] = None
        self.gallery_worker: Optional[GalleryScanWorker] = None

        # Setup UI
        self._init_ui()
        self._apply_theme(self.current_theme)
        self._apply_language(self.current_lang)
        self._setup_logging()
        
        logging.info("Focus GUI (PySide6 / Qt 6) initialized successfully.")
        self.queue_proxy.put(("log", "Welcome to Focus! AI Scenepack Generator ready."))

    def load_settings(self) -> dict:
        default_settings = {
            "pad_before": 2.0, "pad_after": 2.0, "max_gap_tolerance": 1.5,
            "min_scene_duration": 1.0, "frame_skip": 15, "vad_enabled": True,
            "vad_buffer": 300, "vad_speaker_enabled": True, "vad_speaker_threshold": 0.68,
            "play_sound": True, "appearance_mode": "Dark", "theme": "blue",
            "language": "English", "default_mode": "Real Faces"
        }
        settings_path = Path.home() / ".focus_settings.json"
        if not settings_path.exists():
            settings_path = Path("settings.json")
        if settings_path.exists():
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    default_settings.update(loaded)
            except Exception as e:
                logging.warning(f"Failed to load settings from {settings_path}: {e}")
        return default_settings

    def save_current_settings(self, *_):
        try:
            self.settings.update({
                "pad_before": float(self.input_pad_before.text() or 2.0),
                "pad_after": float(self.input_pad_after.text() or 2.0),
                "max_gap_tolerance": float(self.input_max_gap.text() or 1.5),
                "min_scene_duration": float(self.input_min_scene.text() or 1.0),
                "frame_skip": int(self.input_frame_skip.text() or 15),
                "vad_enabled": self.chk_vad.isChecked(),
                "vad_buffer": int(self.input_vad_buffer.text() or 300),
                "vad_speaker_enabled": self.chk_speaker.isChecked(),
                "vad_speaker_threshold": float(self.slider_speaker.value()) / 100.0,
                "play_sound": self.chk_sound.isChecked(),
                "theme": self.combo_theme.currentText(),
                "language": self.combo_lang.currentText(),
                "default_mode": self.current_mode
            })
            settings_path = Path.home() / ".focus_settings.json"
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            logging.debug(f"Note: Could not save settings: {e}")

    def _setup_proxy_connections(self):
        self.queue_proxy.log_signal.connect(self._on_log_msg)
        self.queue_proxy.progress_signal.connect(self._on_progress_update)
        self.queue_proxy.gallery_progress_signal.connect(self._on_gallery_progress)
        self.queue_proxy.gallery_status_signal.connect(self._on_gallery_status)
        self.queue_proxy.gallery_error_signal.connect(self._on_gallery_error)
        self.queue_proxy.gallery_results_signal.connect(self._on_gallery_results)
        self.queue_proxy.gallery_cancelled_signal.connect(self._on_gallery_cancelled)
        self.queue_proxy.show_review_signal.connect(self._on_show_review_checklist)
        self.queue_proxy.render_complete_signal.connect(self._on_render_complete)
        self.queue_proxy.error_signal.connect(self._on_error_msg)
        self.queue_proxy.reset_btn_signal.connect(self._on_reset_buttons)

    def _setup_logging(self):
        handler = QtLogHandler(self.queue_proxy.log_signal)
        handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%H:%M:%S"))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- SIDEBAR NAV ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("SidebarNav")
        self.sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(18, 24, 18, 20)
        sidebar_layout.setSpacing(14)

        self.lbl_logo = QLabel("Focus")
        self.lbl_logo.setObjectName("LogoLabel")
        self.lbl_logo.setFont(QFont("Segoe UI", 22, QFont.Bold))
        sidebar_layout.addWidget(self.lbl_logo)

        self.lbl_wf = QLabel("WORKFLOW")
        self.lbl_wf.setObjectName("SectionHeader")
        sidebar_layout.addWidget(self.lbl_wf)

        self.btn_tutorial = QPushButton("How to Use")
        self.btn_tutorial.setObjectName("SidebarBtn")
        self.btn_tutorial.clicked.connect(self.open_tutorial)
        sidebar_layout.addWidget(self.btn_tutorial)

        self.btn_changelog = QPushButton("Changelog")
        self.btn_changelog.setObjectName("SidebarBtn")
        self.btn_changelog.clicked.connect(self.open_changelog)
        sidebar_layout.addWidget(self.btn_changelog)

        sidebar_layout.addSpacing(10)
        self.lbl_sys = QLabel("SYSTEM")
        self.lbl_sys.setObjectName("SectionHeader")
        sidebar_layout.addWidget(self.lbl_sys)

        self.lbl_theme_title = QLabel("Color Theme:")
        sidebar_layout.addWidget(self.lbl_theme_title)
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["blue", "green", "orange", "red", "indigo", "violet", "pink", "yellow"])
        self.combo_theme.setCurrentText(self.current_theme)
        self.combo_theme.currentTextChanged.connect(self.change_theme_event)
        sidebar_layout.addWidget(self.combo_theme)

        self.lbl_lang_title = QLabel("Language:")
        sidebar_layout.addWidget(self.lbl_lang_title)
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["Polski", "English", "Deutsch", "Русский", "Українська", "Español", "Français", "日本語"])
        self.combo_lang.setCurrentText(self.current_lang)
        self.combo_lang.currentTextChanged.connect(self.change_language_event)
        sidebar_layout.addWidget(self.combo_lang)

        sidebar_layout.addStretch()
        self.chk_sound = QCheckBox("Play sound on complete")
        self.chk_sound.setChecked(self.settings.get("play_sound", True))
        self.chk_sound.toggled.connect(self.save_current_settings)
        sidebar_layout.addWidget(self.chk_sound)

        main_layout.addWidget(self.sidebar)

        # --- MAIN CONTENT AREA ---
        self.content_area = QWidget()
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(16)
        main_layout.addWidget(self.content_area)

        # Header bar (Dashboard + Mode Switch + Tab Switcher)
        header_layout = QHBoxLayout()
        self.lbl_dashboard = QLabel("Dashboard")
        self.lbl_dashboard.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header_layout.addWidget(self.lbl_dashboard)
        header_layout.addStretch()

        # Mode switcher buttons
        self.btn_mode_real = QPushButton("Real Faces")
        self.btn_mode_anime = QPushButton("Anime")
        for b in (self.btn_mode_real, self.btn_mode_anime):
            b.setCheckable(True)
            b.setObjectName("ModeBtn")
        if self.current_mode == "Anime":
            self.btn_mode_anime.setChecked(True)
        else:
            self.btn_mode_real.setChecked(True)
        self.btn_mode_real.clicked.connect(lambda: self._on_mode_switched("Real Faces"))
        self.btn_mode_anime.clicked.connect(lambda: self._on_mode_switched("Anime"))
        
        mode_box = QHBoxLayout()
        mode_box.setSpacing(4)
        mode_box.addWidget(self.btn_mode_real)
        mode_box.addWidget(self.btn_mode_anime)
        header_layout.addLayout(mode_box)
        header_layout.addSpacing(20)

        # Tab Switcher
        self.btn_tab_gen = QPushButton("Generator")
        self.btn_tab_gal = QPushButton("Beta / Character Gallery")
        for b in (self.btn_tab_gen, self.btn_tab_gal):
            b.setCheckable(True)
            b.setObjectName("TabBtn")
        self.btn_tab_gen.setChecked(True)
        self.btn_tab_gen.clicked.connect(lambda: self._switch_main_view(0))
        self.btn_tab_gal.clicked.connect(lambda: self._switch_main_view(1))
        
        tab_box = QHBoxLayout()
        tab_box.setSpacing(4)
        tab_box.addWidget(self.btn_tab_gen)
        tab_box.addWidget(self.btn_tab_gal)
        header_layout.addLayout(tab_box)

        content_layout.addLayout(header_layout)

        # Stacked Widget for Generator vs Gallery
        self.stacked_view = QStackedWidget()
        content_layout.addWidget(self.stacked_view)

        # --- VIEW 0: GENERATOR TAB ---
        self.page_generator = QWidget()
        gen_layout = QVBoxLayout(self.page_generator)
        gen_layout.setContentsMargins(0, 0, 0, 0)
        gen_layout.setSpacing(14)
        self.stacked_view.addWidget(self.page_generator)

        # Scrollable container for Generator
        scroll_gen = QScrollArea()
        scroll_gen.setWidgetResizable(True)
        scroll_gen.setFrameShape(QFrame.NoFrame)
        scroll_gen.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        gen_container = QWidget()
        self.gen_content_layout = QVBoxLayout(gen_container)
        self.gen_content_layout.setContentsMargins(0, 0, 8, 0)
        self.gen_content_layout.setSpacing(14)
        scroll_gen.setWidget(gen_container)
        gen_layout.addWidget(scroll_gen)

        # 1. Hero Banner Card
        hero_card = ModernCard()
        hero_layout = QVBoxLayout(hero_card)
        self.lbl_hero_title = QLabel("Focus - AI Scenepack Generator")
        self.lbl_hero_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.lbl_hero_sub = QLabel("Automated facial tracking and intelligent clip extraction.")
        self.lbl_hero_sub.setObjectName("SubText")
        hero_layout.addWidget(self.lbl_hero_title)
        hero_layout.addWidget(self.lbl_hero_sub)
        self.gen_content_layout.addWidget(hero_card)

        # 2. Settings Card
        settings_card = ModernCard()
        set_layout = QVBoxLayout(settings_card)
        set_layout.setSpacing(12)

        # Top bar: Presets and Aspect Ratio
        top_set_box = QHBoxLayout()
        self.lbl_presets_title = QLabel("Preset Profiles:")
        top_set_box.addWidget(self.lbl_presets_title)
        self.combo_presets = QComboBox()
        self.combo_presets.addItems([
            "Auto-Tune / Zalecane (Automatyczny dobór parametrów)",
            "Fast / TikTok (Szybki montaż, krótkie klipy, małe bufory)",
            "Cinematic / Kinowy (Długie sceny, płynne przejścia, duży bufor)",
            "Ultra-Fast Scan / Szkic (Maksymalne pomijanie klatek, szybki podgląd)"
        ])
        self.combo_presets.currentTextChanged.connect(self._on_preset_selected)
        top_set_box.addWidget(self.combo_presets, 1)

        self.btn_autotune = QPushButton("✨ Auto-Tune")
        self.btn_autotune.setObjectName("AccentBtn")
        self.btn_autotune.clicked.connect(self.apply_auto_tune)
        top_set_box.addWidget(self.btn_autotune)
        top_set_box.addSpacing(15)

        self.lbl_aspect_title = QLabel("Aspect Ratio:")
        top_set_box.addWidget(self.lbl_aspect_title)
        self.combo_aspect = QComboBox()
        self.combo_aspect.addItems(["16:9 Original", "9:16 Vertical", "9:16 Blurred Background"])
        top_set_box.addWidget(self.combo_aspect)
        set_layout.addLayout(top_set_box)

        # Row 1: Numeric Inputs
        inputs_grid = QGridLayout()
        inputs_grid.setSpacing(10)
        
        self.lbl_pad_before = QLabel("Padding Before (s):")
        self.input_pad_before = QLineEdit(str(self.settings.get("pad_before", 2.0)))
        self.lbl_pad_after = QLabel("Padding After (s):")
        self.input_pad_after = QLineEdit(str(self.settings.get("pad_after", 2.0)))
        self.lbl_max_gap = QLabel("Max Gap Tolerance (s):")
        self.input_max_gap = QLineEdit(str(self.settings.get("max_gap_tolerance", 1.5)))
        self.lbl_min_scene = QLabel("Min Scene Length (s):")
        self.input_min_scene = QLineEdit(str(self.settings.get("min_scene_duration", 1.0)))
        self.lbl_frame_skip = QLabel("Frame Skip Interval:")
        self.input_frame_skip = QLineEdit(str(self.settings.get("frame_skip", 15)))

        for edit in (self.input_pad_before, self.input_pad_after, self.input_max_gap, self.input_min_scene, self.input_frame_skip):
            edit.setFixedWidth(60)
            edit.editingFinished.connect(self.save_current_settings)

        inputs_grid.addWidget(self.lbl_pad_before, 0, 0)
        inputs_grid.addWidget(self.input_pad_before, 0, 1)
        inputs_grid.addWidget(self.lbl_pad_after, 0, 2)
        inputs_grid.addWidget(self.input_pad_after, 0, 3)
        inputs_grid.addWidget(self.lbl_max_gap, 0, 4)
        inputs_grid.addWidget(self.input_max_gap, 0, 5)
        inputs_grid.addWidget(self.lbl_min_scene, 0, 6)
        inputs_grid.addWidget(self.input_min_scene, 0, 7)
        inputs_grid.addWidget(self.lbl_frame_skip, 0, 8)
        inputs_grid.addWidget(self.input_frame_skip, 0, 9)
        set_layout.addLayout(inputs_grid)

        # Row 2: VAD & Lip Sync
        vad_box = QHBoxLayout()
        self.chk_vad = QCheckBox("Smart Sentence Protection (VAD & Lip-Sync)")
        self.chk_vad.setChecked(self.settings.get("vad_enabled", True))
        self.chk_vad.toggled.connect(self.save_current_settings)
        vad_box.addWidget(self.chk_vad)
        
        self.lbl_vad_buf = QLabel("Silence Snapping Buffer (ms):")
        vad_box.addWidget(self.lbl_vad_buf)
        self.input_vad_buffer = QLineEdit(str(self.settings.get("vad_buffer", 300)))
        self.input_vad_buffer.setFixedWidth(60)
        self.input_vad_buffer.editingFinished.connect(self.save_current_settings)
        vad_box.addWidget(self.input_vad_buffer)
        vad_box.addStretch()
        set_layout.addLayout(vad_box)

        # Row 3: Target Speaker Voice Matching
        speaker_box = QHBoxLayout()
        self.chk_speaker = QCheckBox("Target Speaker Voice Matching (Filter out background voices)")
        self.chk_speaker.setChecked(self.settings.get("vad_speaker_enabled", True))
        self.chk_speaker.toggled.connect(self.save_current_settings)
        speaker_box.addWidget(self.chk_speaker)

        self.lbl_speaker_thresh = QLabel("Voice Similarity Threshold:")
        speaker_box.addWidget(self.lbl_speaker_thresh)
        
        init_thresh = int(self.settings.get("vad_speaker_threshold", 0.68) * 100)
        self.slider_speaker = QSlider(Qt.Horizontal)
        self.slider_speaker.setRange(10, 99)
        self.slider_speaker.setValue(init_thresh)
        self.slider_speaker.setFixedWidth(150)
        self.lbl_speaker_val = QLabel(f"{init_thresh/100:.2f}")
        self.slider_speaker.valueChanged.connect(lambda v: (self.lbl_speaker_val.setText(f"{v/100:.2f}"), self.save_current_settings()))
        speaker_box.addWidget(self.slider_speaker)
        speaker_box.addWidget(self.lbl_speaker_val)
        speaker_box.addStretch()
        set_layout.addLayout(speaker_box)

        self.gen_content_layout.addWidget(settings_card)

        # 3. Files Selection Card
        files_card = ModernCard()
        files_layout = QVBoxLayout(files_card)
        files_layout.setSpacing(10)

        box_v = QHBoxLayout()
        self.btn_select_video = QPushButton("Select Input Video")
        self.btn_select_video.clicked.connect(self.select_video)
        self.lbl_video_path = QLabel("No video selected")
        self.lbl_video_path.setObjectName("PathLabel")
        box_v.addWidget(self.btn_select_video)
        box_v.addWidget(self.lbl_video_path, 1)
        files_layout.addLayout(box_v)

        box_i = QHBoxLayout()
        self.btn_select_image = QPushButton("Select Reference Face")
        self.btn_select_image.clicked.connect(self.select_image)
        self.lbl_image_path = QLabel("No image selected")
        self.lbl_image_path.setObjectName("PathLabel")
        box_i.addWidget(self.btn_select_image)
        box_i.addWidget(self.lbl_image_path, 1)
        files_layout.addLayout(box_i)

        box_o = QHBoxLayout()
        self.btn_select_output = QPushButton("Select Save Location")
        self.btn_select_output.clicked.connect(self.select_output)
        self.lbl_output_path = QLabel("No save location selected")
        self.lbl_output_path.setObjectName("PathLabel")
        box_o.addWidget(self.btn_select_output)
        box_o.addWidget(self.lbl_output_path, 1)
        files_layout.addLayout(box_o)

        self.gen_content_layout.addWidget(files_card)

        # 4. Action & Progress Card
        action_card = ModernCard()
        action_layout = QVBoxLayout(action_card)
        
        self.btn_generate = QPushButton("1. Scan & Analyze Video")
        self.btn_generate.setObjectName("PrimaryActionBtn")
        self.btn_generate.setFixedHeight(46)
        self.btn_generate.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.btn_generate.clicked.connect(self.start_scan)
        action_layout.addWidget(self.btn_generate)

        prog_box = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        prog_box.addWidget(self.progress_bar, 1)

        self.lbl_eta = QLabel("Ready")
        self.lbl_eta.setObjectName("EtaLabel")
        prog_box.addWidget(self.lbl_eta)
        action_layout.addLayout(prog_box)

        self.gen_content_layout.addWidget(action_card)

        # 5. Review Results Card (hidden initially until scan complete)
        self.review_card = ModernCard()
        self.review_card.setVisible(False)
        rev_layout = QVBoxLayout(self.review_card)
        self.lbl_review_title = QLabel("Step 2: Review & Render Selected Clips")
        self.lbl_review_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        rev_layout.addWidget(self.lbl_review_title)

        self.table_review = QTableWidget(0, 5)
        self.table_review.setHorizontalHeaderLabels(["Include", "Thumbnail", "Start Time", "End Time", "Duration (s)"])
        self.table_review.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_review.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_review.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_review.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_review.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table_review.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_review.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_review.setFixedHeight(220)
        rev_layout.addWidget(self.table_review)

        rev_btns = QHBoxLayout()
        self.btn_play_orig = QPushButton("▶ Play Original Video")
        self.btn_play_orig.clicked.connect(self.play_original)
        rev_btns.addWidget(self.btn_play_orig)

        self.btn_play_res = QPushButton("▶ Play Last Result")
        self.btn_play_res.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.output_path_str)) if self.output_path_str and os.path.exists(self.output_path_str) else None)
        rev_btns.addWidget(self.btn_play_res)

        rev_btns.addStretch()
        self.btn_render = QPushButton("2. Render Selected Clips")
        self.btn_render.setObjectName("PrimaryActionBtn")
        self.btn_render.setFixedHeight(40)
        self.btn_render.clicked.connect(self.start_render)
        rev_btns.addWidget(self.btn_render)
        rev_layout.addLayout(rev_btns)

        self.gen_content_layout.addWidget(self.review_card)

        # 6. Real-time Log Textbox
        log_card = ModernCard()
        log_layout = QVBoxLayout(log_card)
        self.lbl_log_title = QLabel("Execution Logs & Diagnostics:")
        self.lbl_log_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        log_layout.addWidget(self.lbl_log_title)
        
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFixedHeight(140)
        self.txt_log.setObjectName("LogConsole")
        self.txt_log.setFont(QFont("Consolas", 10))
        log_layout.addWidget(self.txt_log)
        self.gen_content_layout.addWidget(log_card)

        # --- VIEW 1: BETA / CHARACTER GALLERY TAB ---
        self.page_gallery = QWidget()
        gal_layout = QVBoxLayout(self.page_gallery)
        gal_layout.setContentsMargins(0, 0, 0, 0)
        gal_layout.setSpacing(14)
        self.stacked_view.addWidget(self.page_gallery)

        gal_top_card = ModernCard()
        gt_layout = QVBoxLayout(gal_top_card)
        self.lbl_gal_title = QLabel("Beta: Automated Character Discovery Gallery")
        self.lbl_gal_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.lbl_gal_sub = QLabel("Scan your video to automatically discover all unique characters. Click any face card to select it as the Reference Face!")
        self.lbl_gal_sub.setObjectName("SubText")
        gt_layout.addWidget(self.lbl_gal_title)
        gt_layout.addWidget(self.lbl_gal_sub)

        gal_btn_box = QHBoxLayout()
        self.btn_gal_scan = QPushButton("Scan Video for Characters")
        self.btn_gal_scan.setObjectName("PrimaryActionBtn")
        self.btn_gal_scan.setFixedHeight(40)
        self.btn_gal_scan.clicked.connect(self.start_gallery_scan)
        gal_btn_box.addWidget(self.btn_gal_scan)

        self.btn_gal_cancel = QPushButton("Cancel Scan")
        self.btn_gal_cancel.setEnabled(False)
        self.btn_gal_cancel.clicked.connect(self.cancel_gallery_scan)
        gal_btn_box.addWidget(self.btn_gal_cancel)
        gal_btn_box.addStretch()
        gt_layout.addLayout(gal_btn_box)

        gal_prog_box = QHBoxLayout()
        self.gal_progress_bar = QProgressBar()
        self.gal_progress_bar.setRange(0, 1000)
        self.gal_progress_bar.setValue(0)
        self.gal_progress_bar.setTextVisible(False)
        self.gal_progress_bar.setFixedHeight(8)
        gal_prog_box.addWidget(self.gal_progress_bar, 1)

        self.lbl_gal_status = QLabel("Ready to scan characters")
        self.lbl_gal_status.setObjectName("EtaLabel")
        gal_prog_box.addWidget(self.lbl_gal_status)
        gt_layout.addLayout(gal_prog_box)
        gal_layout.addWidget(gal_top_card)

        # Gallery Grid Scroll Area
        self.scroll_gal = QScrollArea()
        self.scroll_gal.setWidgetResizable(True)
        self.scroll_gal.setFrameShape(QFrame.NoFrame)
        self.gal_grid_container = QWidget()
        self.gal_grid_layout = QGridLayout(self.gal_grid_container)
        self.gal_grid_layout.setSpacing(16)
        self.gal_grid_layout.setAlignment(Qt.AlignTop)
        self.scroll_gal.setWidget(self.gal_grid_container)
        gal_layout.addWidget(self.scroll_gal)

    def _apply_theme(self, theme_name: str):
        self.current_theme = theme_name
        colors = {
            "blue": ("#2563EB", "#3B82F6", "#1E40AF"),
            "green": ("#10B981", "#34D399", "#047857"),
            "orange": ("#F97316", "#FB923C", "#C2410C"),
            "red": ("#EF4444", "#F87171", "#B91C1C"),
            "indigo": ("#6366F1", "#818CF8", "#4338CA"),
            "violet": ("#8B5CF6", "#A78BFA", "#6D28D9"),
            "pink": ("#EC4899", "#F472B6", "#BE185D"),
            "yellow": ("#F59E0B", "#FBBF24", "#B45309")
        }
        primary, hover, border_glow = colors.get(theme_name, colors["blue"])

        qss = f"""
        QMainWindow, QWidget {{
            background-color: #0B0E14;
            color: #F8FAFC;
            font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
        }}
        QFrame#SidebarNav {{
            background-color: #0E1117;
            border-right: 1px solid #1C1F26;
        }}
        QFrame#ModernCard {{
            background-color: #14161B;
            border: 1px solid #232A36;
            border-radius: 12px;
        }}
        QLabel {{
            color: #F8FAFC;
            background: transparent;
        }}
        QLabel#SubText, QLabel#PathLabel, QLabel#EtaLabel {{
            color: #94A3B8;
        }}
        QLabel#SectionHeader {{
            color: #64748B;
            font-size: 11px;
            font-weight: bold;
        }}
        QLabel#LogoLabel {{
            color: {primary};
        }}
        QPushButton {{
            background-color: #1E232E;
            border: 1px solid #2D3545;
            border-radius: 8px;
            color: #F8FAFC;
            padding: 8px 14px;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: #272E3B;
            border-color: #3B4457;
        }}
        QPushButton:pressed {{
            background-color: #171B24;
        }}
        QPushButton:disabled {{
            background-color: #13171F;
            color: #475569;
            border-color: #1E232E;
        }}
        QPushButton#SidebarBtn {{
            background: transparent;
            border: none;
            text-align: left;
            padding: 10px 14px;
        }}
        QPushButton#SidebarBtn:hover {{
            background-color: #1C2029;
            border-radius: 8px;
        }}
        QPushButton#PrimaryActionBtn, QPushButton#AccentBtn {{
            background-color: {primary};
            border: 1px solid {border_glow};
            color: #FFFFFF;
            font-weight: bold;
        }}
        QPushButton#PrimaryActionBtn:hover, QPushButton#AccentBtn:hover {{
            background-color: {hover};
        }}
        QPushButton#ModeBtn, QPushButton#TabBtn {{
            background-color: #14161B;
            border: 1px solid #232A36;
            border-radius: 6px;
            padding: 6px 16px;
        }}
        QPushButton#ModeBtn:checked, QPushButton#TabBtn:checked {{
            background-color: {primary};
            border-color: {hover};
            color: #FFFFFF;
            font-weight: bold;
        }}
        QLineEdit, QComboBox {{
            background-color: #1A1E26;
            border: 1px solid #2D3545;
            border-radius: 6px;
            color: #F8FAFC;
            padding: 6px 10px;
            selection-background-color: {primary};
        }}
        QLineEdit:focus, QComboBox:focus {{
            border-color: {primary};
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: #14161B;
            border: 1px solid #232A36;
            selection-background-color: {primary};
        }}
        QCheckBox {{
            spacing: 8px;
            background: transparent;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 1px solid #3B4457;
            background-color: #1A1E26;
        }}
        QCheckBox::indicator:checked {{
            background-color: {primary};
            border-color: {hover};
        }}
        QProgressBar {{
            background-color: #1E232E;
            border: none;
            border-radius: 4px;
        }}
        QProgressBar::chunk {{
            background-color: {primary};
            border-radius: 4px;
        }}
        QSlider::groove:horizontal {{
            height: 6px;
            background: #1E232E;
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {primary};
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {hover};
        }}
        QTableWidget {{
            background-color: #14161B;
            border: 1px solid #232A36;
            border-radius: 8px;
            gridline-color: #232A36;
        }}
        QHeaderView::section {{
            background-color: #1A1E26;
            color: #94A3B8;
            padding: 6px;
            border: none;
            border-bottom: 1px solid #232A36;
            font-weight: bold;
        }}
        QTextEdit#LogConsole {{
            background-color: #0E1117;
            border: 1px solid #1C1F26;
            border-radius: 8px;
            color: #38BDF8;
        }}
        """
        self.setStyleSheet(qss)
        self.save_current_settings()

    def _apply_language(self, lang_name: str):
        self.current_lang = lang_name
        self.lbl_dashboard.setText(get_translation(lang_name, "dashboard"))
        if hasattr(self, "lbl_wf"):
            self.lbl_wf.setText(get_translation(lang_name, "sec_workflow"))
        self.btn_tutorial.setText(get_translation(lang_name, "how_to_use"))
        self.btn_changelog.setText(get_translation(lang_name, "changelog"))
        if hasattr(self, "lbl_sys"):
            self.lbl_sys.setText(get_translation(lang_name, "sec_system"))
        self.lbl_theme_title.setText(get_translation(lang_name, "theme"))
        self.lbl_lang_title.setText(get_translation(lang_name, "language"))
        self.chk_sound.setText(get_translation(lang_name, "play_sound"))

        self.btn_mode_real.setText(get_translation(lang_name, "real_faces"))
        self.btn_mode_anime.setText(get_translation(lang_name, "anime"))
        self.btn_tab_gen.setText(get_translation(lang_name, "generator_tab"))
        self.btn_tab_gal.setText(get_translation(lang_name, "gallery_tab"))

        self.lbl_hero_title.setText(get_translation(lang_name, "hero_title"))
        self.lbl_hero_sub.setText(get_translation(lang_name, "hero_subtitle"))
        self.lbl_presets_title.setText(get_translation(lang_name, "preset_label"))
        self.btn_autotune.setText(get_translation(lang_name, "btn_auto_tune"))
        self.lbl_aspect_title.setText(get_translation(lang_name, "aspect_label"))
        self.lbl_pad_before.setText(get_translation(lang_name, "pad_before"))
        self.lbl_pad_after.setText(get_translation(lang_name, "pad_after"))
        self.lbl_max_gap.setText(get_translation(lang_name, "max_gap"))
        self.lbl_min_scene.setText(get_translation(lang_name, "min_scene"))
        self.lbl_frame_skip.setText(get_translation(lang_name, "frame_skip"))
        self.chk_vad.setText(get_translation(lang_name, "vad_enable"))
        self.lbl_vad_buf.setText(get_translation(lang_name, "vad_buffer"))
        self.chk_speaker.setText(get_translation(lang_name, "vad_speaker_enable"))
        self.lbl_speaker_thresh.setText(get_translation(lang_name, "vad_speaker_threshold"))
        self.btn_select_video.setText(get_translation(lang_name, "sel_video"))
        self.btn_select_image.setText(get_translation(lang_name, "sel_ref"))
        self.btn_select_output.setText(get_translation(lang_name, "sel_output"))
        self.btn_generate.setText(get_translation(lang_name, "generate"))
        self.lbl_review_title.setText(get_translation(lang_name, "review_title"))
        self.btn_render.setText(get_translation(lang_name, "btn_render"))
        self.lbl_log_title.setText(get_translation(lang_name, "logs_title"))
        self.lbl_gal_title.setText(get_translation(lang_name, "gallery_title"))
        self.lbl_gal_sub.setText(get_translation(lang_name, "gallery_desc"))
        self.btn_gal_scan.setText(get_translation(lang_name, "scan_chars"))
        self.btn_gal_cancel.setText(get_translation(lang_name, "btn_cancel_gallery"))

        self.btn_play_orig.setText(get_translation(lang_name, "play_orig"))
        self.btn_play_res.setText(get_translation(lang_name, "play_result"))
        self.table_review.setHorizontalHeaderLabels([
            get_translation(lang_name, "th_include"),
            get_translation(lang_name, "th_thumb"),
            get_translation(lang_name, "th_start"),
            get_translation(lang_name, "th_end"),
            get_translation(lang_name, "th_duration")
        ])

        self.combo_presets.blockSignals(True)
        cur_preset_idx = self.combo_presets.currentIndex()
        self.combo_presets.clear()
        self.combo_presets.addItems([
            get_translation(lang_name, "preset_auto"),
            get_translation(lang_name, "preset_fast"),
            get_translation(lang_name, "preset_cinematic"),
            get_translation(lang_name, "preset_draft")
        ])
        if cur_preset_idx >= 0 and cur_preset_idx < self.combo_presets.count():
            self.combo_presets.setCurrentIndex(cur_preset_idx)
        self.combo_presets.blockSignals(False)

        self.combo_aspect.blockSignals(True)
        cur_aspect_idx = self.combo_aspect.currentIndex()
        self.combo_aspect.clear()
        self.combo_aspect.addItems([
            get_translation(lang_name, "aspect_16_9"),
            get_translation(lang_name, "aspect_9_16_vert"),
            get_translation(lang_name, "aspect_9_16_blur")
        ])
        if cur_aspect_idx >= 0 and cur_aspect_idx < self.combo_aspect.count():
            self.combo_aspect.setCurrentIndex(cur_aspect_idx)
        self.combo_aspect.blockSignals(False)

        self.save_current_settings()

    def change_theme_event(self, new_theme: str):
        self._apply_theme(new_theme)

    def change_language_event(self, new_lang: str):
        self._apply_language(new_lang)

    def _on_mode_switched(self, selected_mode: str):
        self.current_mode = selected_mode
        if selected_mode == "Anime":
            self.btn_mode_anime.setChecked(True)
            self.btn_mode_real.setChecked(False)
        else:
            self.btn_mode_real.setChecked(True)
            self.btn_mode_anime.setChecked(False)
        self.save_current_settings()
        self.apply_auto_tune()

    def _switch_main_view(self, index: int):
        self.stacked_view.setCurrentIndex(index)
        if index == 0:
            self.btn_tab_gen.setChecked(True)
            self.btn_tab_gal.setChecked(False)
        else:
            self.btn_tab_gen.setChecked(False)
            self.btn_tab_gal.setChecked(True)

    def open_tutorial(self):
        QMessageBox.information(self, get_translation(self.current_lang, "tutorial_title"), get_translation(self.current_lang, "tutorial_body"))

    def open_changelog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"{get_translation(self.current_lang, 'changelog_title')} ({APP_VERSION})")
        dlg.resize(750, 550)
        dlg.setStyleSheet("background-color: #14161B; color: #FFFFFF;")
        layout = QVBoxLayout(dlg)

        title_lbl = QLabel(f"Focus {APP_VERSION} Release Notes")
        title_lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_lbl.setStyleSheet("color: #FFFFFF; margin-bottom: 10px;")
        layout.addWidget(title_lbl)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setFont(QFont("Segoe UI", 10))
        txt.setStyleSheet("background-color: #1A1D24; color: #E0E0E0; border: 1px solid #2D3139; border-radius: 8px; padding: 10px;")

        msg = (
            f"=== Focus {APP_VERSION} Release Notes ===\n\n"
            "v1.0.6 (Complete Historical Changelog Restoration):\n"
            "• Restored full historical release notes (v0.01 to v1.0.6) across all application interfaces per user request.\n"
            "• Enforced strict versioning rule (+0.01 bump) and validated unit test suite.\n\n"
            "v1.0.5 (Changelog & Documentation Synchronization):\n"
            "• Synchronized release notes history across Qt6 and CustomTkinter interfaces and updated versioning.\n\n"
            "v1.0.4 (OS Abstraction Decoupling):\n"
            "• Decoupled Windows/macOS platform logic into clean backend module (scenepack_generator_backend.py).\n"
            "• Fixed Cocoa GUI activation and app bundling on macOS.\n\n"
            "v1.0.3 (Cross-Platform Stability & Hygiene Update):\n"
            "• Comprehensive Windows & macOS cross-platform fixes and process management.\n"
            "• Elimination of console popups via subprocess CREATE_NO_WINDOW injection.\n"
            "• Complete VideoCapture handle protection (try-finally) preventing file locking.\n"
            "• UTF-8 concat list formatting with forward-slash normalization for FFmpeg.\n"
            "• Immediate background process termination upon scan/render cancellation.\n\n"
            "v1.0.0 / v1.0.2 (Production Release):\n"
            "• Complete migration to PySide6 (Qt 6) with Modern Dark Studio UI.\n"
            "• Automated Zero-Terminal Setup & Launcher for Windows (.bat) and macOS (.sh).\n"
            "• Refined UI typography, professional labels, and polished layout.\n"
            "• Robust multi-language support (English, Polish, German, Spanish, etc.).\n"
            "• Hardware-accelerated FFmpeg scene extraction and concatenation.\n"
            "• Interactive Character Auto-Gallery (AI Detection) for face pre-scanning.\n\n"
            "=== Legacy Development History (v0.01 - v0.95) ===\n\n"
            "v0.95 - Consolidated Windows build to a single standalone Focus.exe (--onefile mode) eliminating redundant launcher files and DLL clutter. Fixed UI color theme persistence across view navigation.\n\n"
            "v0.94 - Fix OpenCV CascadeClassifier missing attribute error in PyInstaller builds and added Windows VBScript zero-console launcher.\n\n"
            "v0.93 - Zero-Terminal Automated Launchers: added double-clickable Uruchom_Focus.command (macOS Gatekeeper auto-clear) and Uruchom_Focus.bat (Windows).\n\n"
            "v0.92 - CI/CD Release Trigger Fix: restored tag trigger pattern in release workflows.\n\n"
            "v0.91 - Critical Windows Execution Fix: added explicit scipy requirement and PyInstaller hidden imports.\n\n"
            "v0.90 - CI/CD GitHub Release Permissions Fix: added explicit write permissions for release notes generation.\n\n"
            "v0.89 - Universal Hardware Acceleration Support: dynamic runtime probing for GPU video encoders across Windows (NVENC/QSV/AMF/MF) and macOS (VideoToolbox).\n\n"
            "v0.88 - Full cross-platform port for Windows 10/11 & macOS with automated FFmpeg static binary downloading.\n\n"
            "v0.87 - Prepared repository for open-source GitHub release: sanitized local system paths and added comprehensive documentation.\n\n"
            "v0.86 - Fixed FFmpeg sub-sampling rendering errors (black line artifacts) on 9:16 crops and unified interface color elements.\n\n"
            "v0.85 - Implemented auto-scrolling log window and dynamic percent progress buttons.\n\n"
            "v0.84 - Implemented Target Speaker Voice Fingerprinting: profiles character voice from verified face frames and filters out non-target speakers.\n\n"
            "v0.83 - Complete UI/UX overhaul inspired by modern dark web dashboards with custom Tkinter animation loops.\n\n"
            "v0.81 - Implemented thumbnail extraction via OpenCV to display video frame previews alongside the checklist.\n\n"
            "v0.80 - Implemented 9:16 Vertical Cropping (Auto-Track & Blurred Background), FFmpeg Scene Cut Snapping, and two-phase Interactive Clip Review Checklist.\n\n"
            "v0.79 - Implemented AI Voice Activity Detection (VAD) & Active Speaker Alignment to intelligently extend scenes to the nearest silence pause.\n\n"
            "v0.74 - Fixed random audio truncation and dropouts by implementing Audio Frame Padding (apad) and 48kHz audio resampler alignment.\n\n"
            "v0.72 - Added Smart Auto-Tune algorithm and dynamic Presets (Anime, Cinematic, Fast Edits).\n\n"
            "v0.71 - Fixed audio/video freeze and frame stalls using hard A/V PTS resampling (-fps_mode cfr, min_hard_comp).\n\n"
            "v0.70 - Internal stability updates and minor UI refinements.\n\n"
            "v0.67 - Restored missing concurrent.futures import in GUI resolving NameError during parallel FFmpeg segment extraction.\n\n"
            "v0.66 - Upgraded Anime face clustering with 1D Hue histogram & 256-bit dHash matching to merge characters across shadows/lighting shifts.\n\n"
            "v0.65 - Added post-scan Face Clustering and Deduplication pass: automatically merges duplicate character captures and selects best thumbnail.\n\n"
            "v0.64 - Fixed macOS Dock app icon rendering using native Cocoa NSApplication icon binding. Enhanced Anime face clustering with center elliptical mask filtering.\n\n"
            "v0.63 - Fixed missing PIL Image import in character gallery pre-scanner.\n\n"
            "v0.62 - Upgraded Anime Character Gallery with 2D HSV Color Histogram + Perceptual dHash Feature Clustering.\n\n"
            "v0.61 - Implemented multi-encoding secondary merge pass for character deduplication in Beta Gallery.\n\n"
            "v0.60 - Fixed Beta character gallery pre-scanner stuck on initialization and wired missing gallery event queue listeners.\n\n"
            "v0.59 - Fixed Beta tab mode localization bug preventing face detection in non-English UI languages. Added live execution logging to GUI console.\n\n"
            "v0.58 - Fixed Beta tab freeze by moving character scanning to a multi-threaded background worker with 2.5s frame stepping.\n\n"
            "v0.57 - Introduced Beta Character Gallery: auto-scans video, clusters unique real/anime faces, and allows one-click character selection.\n\n"
            "v0.56 - Fixed application startup crash by reorganizing variable initialization sequence before UI option menu callbacks.\n\n"
            "v0.55 - Fixed initial 5s stream freeze via accurate seeking buffers (-accurate_seek) and added Minimum Scene Duration filter (1.0s).\n\n"
            "v0.54 - Exhaustive Deep Code Audit: Fully dynamic multi-language tooltips for Real Faces/Anime segmented buttons and thread-safe UI queues.\n\n"
            "v0.53 - Fixed tooltip text updating and localized color theme name mapping.\n\n"
            "v0.52 - Comprehensive Code Audit & Refactoring: Enforced immutability in settings state and strict input boundary validation.\n\n"
            "v0.51 - Extracted clean vector camera logo symbol from ikonka.png to eliminate background box artifacts on macOS Dock squircle tile.\n\n"
            "v0.50 - Added dynamic macOS squircle Dock & window icon generator matching system appearance mode and color theme.\n\n"
            "v0.49 - Updated application icon source to ikonka.png and regenerated native icon.icns bundle assets.\n\n"
            "v0.48 - Added native macOS application icon support (icon.icns) to build script and window header.\n\n"
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
        txt.setText(msg)
        layout.addWidget(txt)

        btn_close = QPushButton(get_translation(self.current_lang, "close") if "close" in TRANSLATIONS.get(self.current_lang, {}) else "Close")
        btn_close.setStyleSheet("background-color: #2D3139; color: #FFFFFF; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        btn_close.clicked.connect(dlg.accept)
        layout.addWidget(btn_close, 0, Qt.AlignCenter)

        dlg.exec()

    def select_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Input Video", "", "Video Files (*.mp4 *.mkv *.mov *.avi *.webm *.flv *.m4v *.ts);;All Files (*.*)")
        if path:
            self.video_path_str = path
            self.lbl_video_path.setText(Path(path).name)
            self.apply_auto_tune()

    def select_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Reference Face", "", "Image Files (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*.*)")
        if path:
            self.image_path_str = path
            self.lbl_image_path.setText(Path(path).name)
            self.selected_ref_data = None

    def select_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Output As", "", "MP4 Video (*.mp4);;All Files (*.*)")
        if path:
            if not path.lower().endswith(".mp4"):
                path += ".mp4"
            self.output_path_str = path
            self.lbl_output_path.setText(Path(path).name)

    def apply_auto_tune(self):
        mode = canonicalize_mode(self.current_mode)
        video_fps = 24.0
        if self.video_path_str and os.path.isfile(self.video_path_str):
            try:
                cap = cv2.VideoCapture(self.video_path_str)
                try:
                    if cap.isOpened():
                        fps_val = cap.get(cv2.CAP_PROP_FPS)
                        if fps_val > 0:
                            video_fps = fps_val
                finally:
                    cap.release()
            except Exception:
                pass

        if mode == "Anime":
            frame_skip, max_gap, pad_before, pad_after, min_scene = max(6, int(video_fps / 3.0)), 1.8, 0.8, 0.8, 0.8
        else:
            frame_skip, max_gap, pad_before, pad_after, min_scene = max(12, int(video_fps / 2.0)), 1.5, 1.5, 1.5, 1.2

        self.input_pad_before.setText(str(pad_before))
        self.input_pad_after.setText(str(pad_after))
        self.input_max_gap.setText(str(max_gap))
        self.input_min_scene.setText(str(min_scene))
        self.input_frame_skip.setText(str(frame_skip))
        self.save_current_settings()

        msg = f"✨ Auto-Tune applied for '{mode}' mode ({video_fps:.1f} FPS)!"
        logging.info(msg)
        self.lbl_eta.setText(msg)

    def _on_preset_selected(self, preset: str):
        idx = self.combo_presets.currentIndex()
        preset_str = preset.lower()
        if idx == 0 or "auto" in preset_str or "zalecan" in preset_str:
            self.apply_auto_tune()
            return
        elif idx == 1 or "fast" in preset_str or "tiktok" in preset_str or "szybk" in preset_str:
            pad_before, pad_after, max_gap, min_scene, frame_skip = 0.4, 0.4, 0.8, 0.5, 8
        elif idx == 2 or "cinematic" in preset_str or "kinow" in preset_str:
            pad_before, pad_after, max_gap, min_scene, frame_skip = 2.0, 2.0, 2.5, 2.0, 15
        elif idx == 3 or "draft" in preset_str or "szkic" in preset_str or "skan" in preset_str:
            pad_before, pad_after, max_gap, min_scene, frame_skip = 1.0, 1.0, 1.5, 1.0, 24
        else:
            self.apply_auto_tune()
            return

        self.input_pad_before.setText(str(pad_before))
        self.input_pad_after.setText(str(pad_after))
        self.input_max_gap.setText(str(max_gap))
        self.input_min_scene.setText(str(min_scene))
        self.input_frame_skip.setText(str(frame_skip))
        self.save_current_settings()
        self.lbl_eta.setText(f"Applied Preset: {preset}")

    def start_scan(self):
        if not self.video_path_str or not self.output_path_str:
            QMessageBox.warning(self, "Missing Files", "Please select both an Input Video and Save Location.")
            return
        if not self.image_path_str and self.selected_ref_data is None:
            QMessageBox.warning(self, "Missing Reference", "Please select a Reference Face Image or choose a character from the Beta Gallery.")
            return

        try:
            pad_before = max(0.0, float(self.input_pad_before.text() or 2.0))
            pad_after = max(0.0, float(self.input_pad_after.text() or 2.0))
            max_gap = max(0.0, float(self.input_max_gap.text() or 1.5))
            min_scene = max(0.0, float(self.input_min_scene.text() or 1.0))
            skip = max(1, int(self.input_frame_skip.text() or 15))
            vad_enabled = self.chk_vad.isChecked()
            vad_buffer = max(50, int(self.input_vad_buffer.text() or 300))
            vad_speaker_enabled = self.chk_speaker.isChecked()
            vad_speaker_threshold = float(self.slider_speaker.value()) / 100.0
        except ValueError:
            QMessageBox.showerror(self, "Invalid Input", "Numeric parameters must be valid numbers.")
            return

        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("Scanning & Analyzing... (Please Wait)")
        self.progress_bar.setValue(0)
        self.lbl_eta.setText("Initializing scan...")
        self.review_card.setVisible(False)
        self.table_review.setRowCount(0)

        ref_image_to_pass = self.image_path_str if self.image_path_str else self.selected_ref_data

        self.scan_worker = ScanWorker(
            ScenePackGenerator, self.video_path_str, ref_image_to_pass,
            pad_before, pad_after, max_gap, min_scene, skip,
            vad_enabled, vad_buffer, vad_speaker_enabled, vad_speaker_threshold,
            self.current_mode, self.queue_proxy
        )
        self.scan_worker.start()

    def start_render(self):
        selected_intervals = []
        for (interval, chk) in self.review_checkboxes:
            if chk.isChecked():
                selected_intervals.append(interval)

        if not selected_intervals:
            QMessageBox.warning(self, "No Clips Selected", "Please select at least one clip in the table to render.")
            return

        self.btn_render.setEnabled(False)
        self.btn_render.setText("Rendering Clips...")
        self.progress_bar.setValue(0)
        self.lbl_eta.setText("Extracting and concatenating clips...")

        idx_aspect = self.combo_aspect.currentIndex()
        if idx_aspect == 1:
            aspect_canonical = "9:16 Vertical (Auto-Track)"
        elif idx_aspect == 2:
            aspect_canonical = "9:16 Blurred Background"
        else:
            aspect_canonical = "16:9 Original"

        generator_inst = getattr(self.scan_worker, "generator_instance", None) if self.scan_worker else ScenePackGenerator(self.queue_proxy, 15, self.current_mode)
        self.render_worker = RenderWorker(
            generator_inst, self.video_path_str, selected_intervals,
            self.output_path_str, aspect_canonical, self.queue_proxy
        )
        self.render_worker.start()

    def start_gallery_scan(self):
        if not self.video_path_str or not os.path.isfile(self.video_path_str):
            QMessageBox.warning(self, "No Input Video", "Please select a valid input video file in the Generator tab first!")
            return

        self.btn_gal_scan.setEnabled(False)
        self.btn_gal_cancel.setEnabled(True)
        self.gal_progress_bar.setValue(0)
        self.lbl_gal_status.setText("Initializing background character pre-scan...")

        self.gallery_worker = GalleryScanWorker(sg_engine, self.video_path_str, self.current_mode, self.queue_proxy)
        self.gallery_worker.start()

    def cancel_gallery_scan(self):
        if self.gallery_worker:
            self.gallery_worker.cancel()
        self.lbl_gal_status.setText("Cancelling scan...")
        self.btn_gal_cancel.setEnabled(False)

    def play_original(self):
        if self.video_path_str and os.path.exists(self.video_path_str):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.video_path_str))

    # --- SIGNAL SLOTS ---
    @Slot(str)
    def _on_log_msg(self, msg: str):
        self.txt_log.append(msg)
        # Auto scroll to bottom
        scrollbar = self.txt_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @Slot(float, str)
    def _on_progress_update(self, val: float, status: str):
        self.progress_bar.setValue(int(val * 1000))
        self.lbl_eta.setText(status)

    @Slot(float, str)
    def _on_gallery_progress(self, val: float, status: str):
        self.gal_progress_bar.setValue(int(val * 1000))
        self.lbl_gal_status.setText(status)

    @Slot(str)
    def _on_gallery_status(self, status: str):
        self.lbl_gal_status.setText(status)

    @Slot(str)
    def _on_gallery_error(self, err: str):
        self.lbl_gal_status.setText(f"Error: {err}")
        self.btn_gal_scan.setEnabled(True)
        self.btn_gal_cancel.setEnabled(False)
        QMessageBox.critical(self, "Gallery Error", err)

    @Slot(list)
    def _on_gallery_results(self, clusters: list):
        self._populate_gallery_grid(clusters)
        self.btn_gal_scan.setEnabled(True)
        self.btn_gal_cancel.setEnabled(False)
        self.lbl_gal_status.setText(f"Scan complete! Found {len(clusters)} unique character profile(s).")

    @Slot(list)
    def _on_gallery_cancelled(self, clusters: list):
        self._populate_gallery_grid(clusters)
        self.btn_gal_scan.setEnabled(True)
        self.btn_gal_cancel.setEnabled(False)
        self.lbl_gal_status.setText(f"Scan cancelled. Found {len(clusters)} character profile(s).")

    def _populate_gallery_grid(self, clusters: list):
        # Clear grid
        while self.gal_grid_layout.count():
            item = self.gal_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not clusters:
            lbl = QLabel("No characters found in video.")
            self.gal_grid_layout.addWidget(lbl, 0, 0)
            return

        cols = 4
        for idx, cluster in enumerate(clusters):
            r = idx // cols
            c = idx % cols
            
            card = ModernCard()
            c_layout = QVBoxLayout(card)
            c_layout.setAlignment(Qt.AlignCenter)
            c_layout.setSpacing(8)

            img_label = QLabel()
            img_label.setAlignment(Qt.AlignCenter)
            crop_path = cluster.get("crop_path")
            if crop_path and os.path.exists(crop_path):
                pixmap = QPixmap(crop_path).scaled(110, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_label.setPixmap(pixmap)
            else:
                img_label.setText("No Image")
            c_layout.addWidget(img_label)

            lbl_name = QLabel(f"Character #{cluster['id']}")
            lbl_name.setFont(QFont("Segoe UI", 11, QFont.Bold))
            lbl_name.setAlignment(Qt.AlignCenter)
            c_layout.addWidget(lbl_name)

            lbl_count = QLabel(f"{cluster['count']} detection(s)")
            lbl_count.setObjectName("SubText")
            lbl_count.setAlignment(Qt.AlignCenter)
            c_layout.addWidget(lbl_count)

            btn_sel = QPushButton("Select as Reference")
            btn_sel.setObjectName("AccentBtn")
            btn_sel.clicked.connect(lambda chk=False, cl=cluster: self._select_gallery_character(cl))
            c_layout.addWidget(btn_sel)

            self.gal_grid_layout.addWidget(card, r, c)

    def _select_gallery_character(self, cluster: dict):
        self.selected_ref_data = cluster
        self.image_path_str = ""
        self.lbl_image_path.setText(f"[Beta Gallery] Character #{cluster['id']} ({cluster['count']} detections)")
        self._switch_main_view(0)
        msg = f"Selected Character #{cluster['id']} as Reference Face! Ready to scan in Generator tab."
        logging.info(msg)
        self.lbl_eta.setText(msg)
        QMessageBox.information(self, "Character Selected", msg)

    @Slot(list, list)
    def _on_show_review_checklist(self, intervals: list, thumbnails: list):
        self.scanned_intervals = intervals
        self.review_checkboxes = []
        self.table_review.setRowCount(len(intervals))
        self.table_review.setRowHeight(0, 95)

        for idx, (start, end, avg_x) in enumerate(intervals):
            self.table_review.setRowHeight(idx, 95)
            
            # Col 0: Checkbox
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            chk = QCheckBox()
            chk.setChecked(True)
            chk_layout.addWidget(chk)
            self.table_review.setCellWidget(idx, 0, chk_widget)
            self.review_checkboxes.append(((start, end, avg_x), chk))

            # Col 1: Thumbnail
            thumb_label = QLabel()
            thumb_label.setAlignment(Qt.AlignCenter)
            if idx < len(thumbnails) and thumbnails[idx] is not None:
                pil_img = thumbnails[idx]
                data = pil_img.convert("RGBA").tobytes("raw", "RGBA")
                qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format_RGBA8888)
                pixmap = QPixmap.fromImage(qimg)
                thumb_label.setPixmap(pixmap)
            else:
                thumb_label.setText("No Thumb")
            self.table_review.setCellWidget(idx, 1, thumb_label)

            # Col 2, 3, 4: Times
            item_start = QTableWidgetItem(f"{start:.2f}s")
            item_start.setTextAlignment(Qt.AlignCenter)
            self.table_review.setItem(idx, 2, item_start)

            item_end = QTableWidgetItem(f"{end:.2f}s")
            item_end.setTextAlignment(Qt.AlignCenter)
            self.table_review.setItem(idx, 3, item_end)

            item_dur = QTableWidgetItem(f"{end - start:.2f}s")
            item_dur.setTextAlignment(Qt.AlignCenter)
            self.table_review.setItem(idx, 4, item_dur)

        self.review_card.setVisible(True)
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText(get_translation(self.current_lang, "btn_generate"))
        self.lbl_eta.setText(f"Scan complete! Review {len(intervals)} clip(s) below and click Render.")

    @Slot(str)
    def _on_render_complete(self, out_path: str):
        self.btn_render.setEnabled(True)
        self.btn_render.setText(get_translation(self.current_lang, "btn_render"))
        self.progress_bar.setValue(1000)
        self.lbl_eta.setText(f"✨ Rendering complete! Saved to: {Path(out_path).name}")
        if self.chk_sound.isChecked():
            QApplication.beep()
        QMessageBox.information(self, "Success", f"Scenepack successfully rendered and saved to:\n{out_path}")

    @Slot(str)
    def _on_error_msg(self, err: str):
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText(get_translation(self.current_lang, "btn_generate"))
        self.btn_render.setEnabled(True)
        self.btn_render.setText(get_translation(self.current_lang, "btn_render"))
        QMessageBox.critical(self, "Execution Error", f"An error occurred:\n{err}")

    @Slot()
    def _on_reset_buttons(self):
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText(get_translation(self.current_lang, "btn_generate"))
        self.btn_render.setEnabled(True)
        self.btn_render.setText(get_translation(self.current_lang, "btn_render"))

    def closeEvent(self, event):
        logging.info("Shutting down Focus GUI...")
        self.save_current_settings()
        if self.gallery_worker and self.gallery_worker.isRunning():
            self.gallery_worker.cancel()
            self.gallery_worker.wait(1000)
        if self.scan_worker and self.scan_worker.isRunning():
            if hasattr(self.scan_worker, 'cancel'):
                self.scan_worker.cancel()
            self.scan_worker.terminate()
        if self.render_worker and self.render_worker.isRunning():
            if hasattr(self.render_worker, 'cancel'):
                self.render_worker.cancel()
            self.render_worker.terminate()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    if sys.platform == "darwin":
        app.setQuitOnLastWindowClosed(True)
    window = FocusApp()
    window.show()
    window.raise_()
    window.activateWindow()
    if sys.platform == "darwin":
        # On macOS Cocoa, calling activateWindow() before app.exec() starts the event loop can be ignored.
        # Single-shot timers inside the event loop force Cocoa to bring the window to front and give it key status.
        def _force_macos_focus():
            window.show()
            window.raise_()
            window.activateWindow()
        QTimer.singleShot(100, _force_macos_focus)
        QTimer.singleShot(500, _force_macos_focus)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
