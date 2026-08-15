import os
import sys
import json
import logging
import subprocess
import platform
from pathlib import Path
from typing import List, Tuple, Optional

# macOS specific GUI fixes to prevent Cocoa/Qt/OpenCV collisions and window hiding
if sys.platform == "darwin":
    os.environ["QT_MAC_WANTS_LAYER"] = "1"
    os.environ["OPENCV_UI_BACKEND"] = "none"

import cv2

from PySide6.QtCore import Qt, QUrl, QTimer, Slot, QRectF, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QSequentialAnimationGroup, QPoint
from PySide6.QtGui import QFont, QPixmap, QImage, QDesktopServices, QPainter, QColor, QPen, QIcon, QLinearGradient
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QCheckBox, QSlider, QProgressBar, QComboBox,
    QScrollArea, QTabWidget, QFrame, QMessageBox, QFileDialog, QTextEdit,
    QSplitter, QStackedWidget, QButtonGroup, QRadioButton, QAbstractItemView,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QDialog, QSplashScreen,
    QGraphicsOpacityEffect, QListWidget, QListWidgetItem
)
import gc

# Import shared backend engine and helpers from scenepack_generator_backend
import scenepack_generator_backend as sg_engine
from scenepack_generator_backend import (
    ScenePackGenerator, get_translation, canonicalize_mode, APP_VERSION, get_changelog_text, get_app_dir, parse_video_paths, natural_sort_key
)
from scenepack_generator_workers_qt import (
    QtLogHandler, QtQueueProxy, ScanWorker, RenderWorker, GalleryScanWorker, AudioTrackWorker, MasterConcatWorker
)

def fix_qt_ampersand(text: str) -> str:
    if not text:
        return ""
    import re
    return re.sub(r'(?<!&)&(?!&)', '&&', text)

def get_application_icon() -> QIcon:
    """Load or programmatically render high-resolution Focus window and taskbar icon."""
    possible_paths = [
        Path(get_app_dir()) / "icon.png",
        Path(__file__).parent / "icon.png",
        Path(__file__).parent / "ikonka.png",
        Path(__file__).parent / "icon.icns",
    ]
    for p in possible_paths:
        if p.exists() and p.is_file():
            ic = QIcon(str(p.resolve()))
            if not ic.isNull():
                return ic

    # Vector fallback render if no icon image file exists
    size = 256
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor("#8B5CF6"))
    grad.setColorAt(1.0, QColor("#6D28D9"))
    painter.setBrush(grad)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, size, size, 48, 48)
    
    pen = QPen(QColor("#FFFFFF"), 24, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawPolyline([
        QPoint(76, 64), QPoint(180, 64),
        QPoint(76, 64), QPoint(76, 192),
    ])
    painter.drawPolyline([
        QPoint(76, 124), QPoint(156, 124)
    ])
    painter.end()
    return QIcon(pix)

def get_system_font(size: int = 10, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """Returns native system font (San Francisco on macOS, Segoe UI on Windows)."""
    family = ".AppleSystemUIFont" if sys.platform == "darwin" else "Segoe UI"
    return QFont(family, size, weight)

class ModernCard(QFrame):
    """Rounded container frame with border styling for grouping UI elements."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ModernCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

class ToastNotification(QFrame):
    """Modern floating Toast Notification overlay at top-right."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToastNotification")
        self.setStyleSheet("""
            QFrame#ToastNotification {
                background-color: rgba(20, 24, 33, 0.95);
                border: 1px solid rgba(0, 229, 255, 0.5);
                border-radius: 8px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        self.lbl_icon = QLabel("✨")
        self.lbl_icon.setFont(get_system_font(12))
        layout.addWidget(self.lbl_icon)
        
        self.lbl_msg = QLabel("")
        self.lbl_msg.setFont(get_system_font(10, QFont.Weight.Bold))
        self.lbl_msg.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(self.lbl_msg)
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.hide()
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fade_out)

    def show_toast(self, text: str, icon: str = "✨", duration_ms: int = 3200):
        self.lbl_msg.setText(text)
        self.lbl_icon.setText(icon)
        self.adjustSize()
        if self.parent():
            p_rect = self.parent().rect()
            self.move(p_rect.width() - self.width() - 24, 24)
            self.raise_()
        
        self.show()
        self.opacity_effect.setOpacity(0.0)
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.anim.setDuration(250)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)
        self.anim.start()
        
        self.timer.start(duration_ms)

    def fade_out(self):
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.anim.setDuration(300)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.InQuad)
        self.anim.finished.connect(self.hide)
        self.anim.start()

class MiniPreviewDialog(QDialog):
    """Mini-preview dialog showing segment preview information and option to play."""
    def __init__(self, parent, video_path: str, start_sec: float, end_sec: float):
        super().__init__(parent)
        self.setWindowTitle(f"Clip Preview ({start_sec:.2f}s - {end_sec:.2f}s)")
        self.setMinimumSize(440, 260)
        self.video_path = video_path
        self.start_sec = start_sec
        self.end_sec = end_sec

        layout = QVBoxLayout(self)
        
        lbl_info = QLabel(f"<b>Video:</b> {Path(video_path).name}<br><b>Segment:</b> {start_sec:.2f}s to {end_sec:.2f}s (Duration: {end_sec - start_sec:.2f}s)")
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)

        self.lbl_frame = QLabel()
        self.lbl_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_frame.setFixedHeight(150)
        layout.addWidget(self.lbl_frame)

        self._load_preview_frame()

        btn_layout = QHBoxLayout()
        btn_play = QPushButton("▶️ Play Video in System Player")
        btn_play.clicked.connect(self._play_video)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_play)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _load_preview_frame(self):
        try:
            cap = cv2.VideoCapture(self.video_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(self.start_sec * fps))
            ret, frame = cap.read()
            cap.release()

            if ret and frame is not None:
                h, w = frame.shape[:2]
                new_w = 320
                new_h = int(h * (new_w / w))
                frame_resized = cv2.resize(frame, (new_w, new_h))
                rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                qimg = QImage(rgb.data, new_w, new_h, new_w * 3, QImage.Format.Format_RGB888)
                self.lbl_frame.setPixmap(QPixmap.fromImage(qimg))
            else:
                self.lbl_frame.setText("Preview frame unavailable")
        except Exception as e:
            logging.error(f"Failed to load preview frame: {e}")
            self.lbl_frame.setText("Preview frame unavailable")

    def _play_video(self):
        if self.video_path and os.path.exists(self.video_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.video_path))

class FocusApp(QMainWindow):
    """
    Main Application Window in PySide6 (Qt 6).
    Replaces CustomTkinter with a high-performance, responsive Modern Dark Studio UI.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Focus - AI Scenepack Generator ({APP_VERSION})")
        self.setWindowIcon(get_application_icon())
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
        self.audio_worker: Optional[AudioTrackWorker] = None

        self.batch_queue_files: List[str] = []
        self.current_batch_index: int = -1
        self.is_batch_running: bool = False

        # Setup UI
        self._init_ui()
        self.toast = ToastNotification(self)
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
                "export_quality": self.combo_export_quality.currentText(),
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
        self.queue_proxy.audio_tracks_signal.connect(self._on_audio_tracks_loaded)
        self.queue_proxy.master_concat_complete_signal.connect(self._on_master_concat_complete)
        self.queue_proxy.episode_progress_signal.connect(self._on_episode_progress)

    @Slot(list)
    def _on_audio_tracks_loaded(self, tracks):
        self.combo_audio_track.clear()
        for stream_idx, label in tracks:
            self.combo_audio_track.addItem(label, stream_idx)
        valid_paths = self.get_input_video_paths()
        if hasattr(self, 'lbl_video_path') and valid_paths:
            if len(valid_paths) == 1:
                self.lbl_video_path.setText(valid_paths[0].name)
            else:
                names = [p.name for p in valid_paths]
                if len(names) <= 2:
                    display_txt = f"🎬 {len(valid_paths)} Videos Selected ({', '.join(names)})"
                else:
                    display_txt = f"🎬 {len(valid_paths)} Videos Selected ({names[0]}, {names[1]}... +{len(names)-2} more)"
                self.lbl_video_path.setText(display_txt)

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

        self.lbl_logo = QLabel("🎯 FOCUS")
        self.lbl_logo.setObjectName("LogoText")
        self.lbl_logo.setFont(get_system_font(22, QFont.Weight.Bold))
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
        self.lbl_dashboard.setFont(get_system_font(20, QFont.Weight.Bold))
        header_layout.addWidget(self.lbl_dashboard)
        header_layout.addStretch(1)

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
        header_layout.addSpacing(12)

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

        # 1. Quick Presets Toolbar
        self.presets_card = ModernCard(self)
        presets_layout = QHBoxLayout(self.presets_card)
        presets_layout.setContentsMargins(14, 10, 14, 10)
        presets_layout.setSpacing(10)

        lbl_presets_head = QLabel("⚡ Quick Presets:")
        lbl_presets_head.setFont(get_system_font(11, QFont.Weight.Bold))
        presets_layout.addWidget(lbl_presets_head)

        self.btn_autotune = QPushButton("✨ Auto-Tune")
        self.btn_autotune.setObjectName("AccentBtn")
        self.btn_autotune.clicked.connect(self.apply_auto_tune)
        presets_layout.addWidget(self.btn_autotune)

        self.btn_preset_tiktok = QPushButton("📱 TikTok / Shorts (9:16)")
        self.btn_preset_tiktok.clicked.connect(lambda: self._apply_smart_preset("tiktok"))
        presets_layout.addWidget(self.btn_preset_tiktok)

        self.btn_preset_youtube = QPushButton("🎬 YouTube (16:9)")
        self.btn_preset_youtube.clicked.connect(lambda: self._apply_smart_preset("youtube"))
        presets_layout.addWidget(self.btn_preset_youtube)

        self.btn_preset_draft = QPushButton("🚀 Fast Draft Scan")
        self.btn_preset_draft.clicked.connect(lambda: self._apply_smart_preset("draft"))
        presets_layout.addWidget(self.btn_preset_draft)

        presets_layout.addStretch()
        self.gen_content_layout.addWidget(self.presets_card)

        # 2. Unified Media & Reference Hub
        self.files_card = ModernCard(self)
        files_layout = QVBoxLayout(self.files_card)
        files_layout.setContentsMargins(16, 14, 16, 14)
        files_layout.setSpacing(10)

        # Row 1: Video selection + Folder + Clear + Master/Separate output mode
        top_v_row = QHBoxLayout()
        self.btn_select_video = QPushButton("📁 Select Video(s)...")
        self.btn_select_video.setObjectName("AccentBtn")
        self.btn_select_video.clicked.connect(self.select_video)
        top_v_row.addWidget(self.btn_select_video)

        self.btn_select_folder = QPushButton("📂 Add Folder...")
        self.btn_select_folder.clicked.connect(self.add_folder_videos)
        top_v_row.addWidget(self.btn_select_folder)

        self.btn_clear_batch = QPushButton("🗑️ Clear")
        self.btn_clear_batch.clicked.connect(self.clear_batch_queue)
        top_v_row.addWidget(self.btn_clear_batch)

        top_v_row.addSpacing(16)
        lbl_batch_mode = QLabel("Output Mode:")
        lbl_batch_mode.setFont(get_system_font(10, QFont.Weight.Bold))
        top_v_row.addWidget(lbl_batch_mode)

        self.radio_batch_single = QRadioButton("📦 Master Scenepack (Single Video)")
        self.radio_batch_separate = QRadioButton("📁 Separate Episode Files")
        self.radio_batch_single.setChecked(True)
        top_v_row.addWidget(self.radio_batch_single)
        top_v_row.addWidget(self.radio_batch_separate)
        top_v_row.addStretch()
        files_layout.addLayout(top_v_row)

        # Row 2: Selected Videos Status Badge
        self.lbl_video_path = QLabel("No video selected")
        self.lbl_video_path.setObjectName("PathLabel")
        self.lbl_video_path.setStyleSheet("background-color: #1A1E26; border: 1px solid #2D3545; border-radius: 6px; padding: 6px 12px; font-weight: 500;")
        files_layout.addWidget(self.lbl_video_path)

        # Row 3: Reference Face & Output Save Location (Clean 2-column)
        ref_out_grid = QGridLayout()
        ref_out_grid.setSpacing(10)

        self.btn_select_image = QPushButton("👤 Select Reference Face")
        self.btn_select_image.clicked.connect(self.select_image)
        self.lbl_image_path = QLabel("No image selected")
        self.lbl_image_path.setObjectName("PathLabel")
        self.lbl_image_path.setStyleSheet("background-color: #1A1E26; border: 1px solid #2D3545; border-radius: 6px; padding: 6px 12px;")
        ref_out_grid.addWidget(self.btn_select_image, 0, 0)
        ref_out_grid.addWidget(self.lbl_image_path, 0, 1)

        self.btn_select_output = QPushButton("💾 Select Save Location")
        self.btn_select_output.clicked.connect(self.select_output)
        self.lbl_output_path = QLabel("No save location selected")
        self.lbl_output_path.setObjectName("PathLabel")
        self.lbl_output_path.setStyleSheet("background-color: #1A1E26; border: 1px solid #2D3545; border-radius: 6px; padding: 6px 12px;")
        ref_out_grid.addWidget(self.btn_select_output, 1, 0)
        ref_out_grid.addWidget(self.lbl_output_path, 1, 1)

        ref_out_grid.setColumnStretch(1, 1)
        files_layout.addLayout(ref_out_grid)

        # Row 4: Audio Track Selector
        box_a = QHBoxLayout()
        self.lbl_audio_track = QLabel("🎧 Audio Track:")
        self.combo_audio_track = QComboBox()
        self.combo_audio_track.addItem("Default Audio Stream (Track 1)", 0)
        box_a.addWidget(self.lbl_audio_track)
        box_a.addWidget(self.combo_audio_track, 1)
        files_layout.addLayout(box_a)

        self.gen_content_layout.addWidget(self.files_card)

        # 3. Tuning & Speech Protection Card
        self.settings_card = ModernCard(self)
        set_layout = QVBoxLayout(self.settings_card)
        set_layout.setContentsMargins(16, 14, 16, 14)
        set_layout.setSpacing(12)

        lbl_settings_head = QLabel("⚙️ Scene & Detection Tuning")
        lbl_settings_head.setFont(get_system_font(11, QFont.Weight.Bold))
        set_layout.addWidget(lbl_settings_head)

        inputs_grid = QGridLayout()
        inputs_grid.setSpacing(10)

        self.lbl_pad_before = QLabel("Padding Before (s):")
        self.input_pad_before = QLineEdit(str(self.settings.get("pad_before", 2.0)))
        self.lbl_pad_after = QLabel("Padding After (s):")
        self.input_pad_after = QLineEdit(str(self.settings.get("pad_after", 2.0)))
        self.lbl_max_gap = QLabel("Max Gap (s):")
        self.input_max_gap = QLineEdit(str(self.settings.get("max_gap_tolerance", 1.5)))

        self.lbl_min_scene = QLabel("Min Scene (s):")
        self.input_min_scene = QLineEdit(str(self.settings.get("min_scene_duration", 1.0)))
        self.lbl_frame_skip = QLabel("Frame Skip:")
        self.input_frame_skip = QLineEdit(str(self.settings.get("frame_skip", 15)))
        self.lbl_aspect_title = QLabel("Aspect Ratio:")
        self.combo_aspect = QComboBox()
        self.combo_aspect.addItems(["16:9 Original", "9:16 Vertical", "9:16 Blurred Background"])

        self.lbl_quality_title = QLabel("Export Quality:")
        self.combo_export_quality = QComboBox()
        self.combo_export_quality.addItems(["High (CRF 16)", "Medium (CRF 20)", "Low (CRF 24)"])
        self.combo_export_quality.setCurrentText(self.settings.get("export_quality", "Medium (CRF 20)"))
        self.combo_export_quality.currentTextChanged.connect(self.save_current_settings)

        for edit in (self.input_pad_before, self.input_pad_after, self.input_max_gap, self.input_min_scene, self.input_frame_skip):
            edit.setFixedWidth(55)
            edit.editingFinished.connect(self.save_current_settings)

        # Row 0
        inputs_grid.addWidget(self.lbl_pad_before, 0, 0)
        inputs_grid.addWidget(self.input_pad_before, 0, 1)
        inputs_grid.addWidget(self.lbl_pad_after, 0, 2)
        inputs_grid.addWidget(self.input_pad_after, 0, 3)
        inputs_grid.addWidget(self.lbl_max_gap, 0, 4)
        inputs_grid.addWidget(self.input_max_gap, 0, 5)

        # Row 1
        inputs_grid.addWidget(self.lbl_min_scene, 1, 0)
        inputs_grid.addWidget(self.input_min_scene, 1, 1)
        inputs_grid.addWidget(self.lbl_frame_skip, 1, 2)
        inputs_grid.addWidget(self.input_frame_skip, 1, 3)
        inputs_grid.addWidget(self.lbl_aspect_title, 1, 4)
        inputs_grid.addWidget(self.combo_aspect, 1, 5)

        # Row 2
        inputs_grid.addWidget(self.lbl_quality_title, 2, 0)
        inputs_grid.addWidget(self.combo_export_quality, 2, 1, 1, 5)

        set_layout.addLayout(inputs_grid)

        # VAD & Speaker protection row
        vad_box = QHBoxLayout()
        self.chk_vad = QCheckBox("Smart Sentence Protection (VAD & Lip-Sync)")
        self.chk_vad.setChecked(self.settings.get("vad_enabled", True))
        self.chk_vad.toggled.connect(self.save_current_settings)
        vad_box.addWidget(self.chk_vad)

        self.lbl_vad_buf = QLabel("Silence Buffer (ms):")
        vad_box.addWidget(self.lbl_vad_buf)
        self.input_vad_buffer = QLineEdit(str(self.settings.get("vad_buffer", 300)))
        self.input_vad_buffer.setFixedWidth(55)
        self.input_vad_buffer.editingFinished.connect(self.save_current_settings)
        vad_box.addWidget(self.input_vad_buffer)
        vad_box.addStretch()
        set_layout.addLayout(vad_box)

        speaker_box = QHBoxLayout()
        self.chk_speaker = QCheckBox("Target Speaker Voice Matching")
        self.chk_speaker.setChecked(self.settings.get("vad_speaker_enabled", True))
        self.chk_speaker.toggled.connect(self.save_current_settings)
        speaker_box.addWidget(self.chk_speaker)

        self.lbl_speaker_thresh = QLabel("Similarity:")
        speaker_box.addWidget(self.lbl_speaker_thresh)

        init_thresh = int(self.settings.get("vad_speaker_threshold", 0.68) * 100)
        self.slider_speaker = QSlider(Qt.Horizontal)
        self.slider_speaker.setRange(10, 99)
        self.slider_speaker.setValue(init_thresh)
        self.slider_speaker.setFixedWidth(130)
        self.lbl_speaker_val = QLabel(f"{init_thresh/100:.2f}")
        self.slider_speaker.valueChanged.connect(lambda v: (self.lbl_speaker_val.setText(f"{v/100:.2f}"), self.save_current_settings()))
        speaker_box.addWidget(self.slider_speaker)
        speaker_box.addWidget(self.lbl_speaker_val)
        speaker_box.addStretch()
        set_layout.addLayout(speaker_box)

        self.gen_content_layout.addWidget(self.settings_card)

        # 4. Action & Multi-Episode Progress Card
        self.action_card = ModernCard(self)
        action_layout = QVBoxLayout(self.action_card)
        action_layout.setContentsMargins(16, 14, 16, 14)
        action_layout.setSpacing(10)

        self.btn_generate = QPushButton("▶ 1. Start Scan & Analyze Video")
        self.btn_generate.setObjectName("PrimaryActionBtn")
        self.btn_generate.setFixedHeight(46)
        self.btn_generate.setFont(get_system_font(13, QFont.Weight.Bold))
        self.btn_generate.clicked.connect(self.start_scan)
        action_layout.addWidget(self.btn_generate)

        # Multi-Episode Badge (Hidden by default, shown during multi-video jobs)
        self.lbl_episode_badge = QLabel("🎬 Episode [1/1]: Ready")
        self.lbl_episode_badge.setObjectName("EpisodeBadge")
        self.lbl_episode_badge.setVisible(False)
        action_layout.addWidget(self.lbl_episode_badge)

        # Current Episode Progress Bar
        self.episode_progress_bar = QProgressBar()
        self.episode_progress_bar.setObjectName("EpisodeProgressBar")
        self.episode_progress_bar.setRange(0, 1000)
        self.episode_progress_bar.setValue(0)
        self.episode_progress_bar.setTextVisible(False)
        self.episode_progress_bar.setFixedHeight(6)
        self.episode_progress_bar.setVisible(False)
        action_layout.addWidget(self.episode_progress_bar)

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

        self.gen_content_layout.addWidget(self.action_card)

        # 5. Review Results Card (hidden initially until scan complete)
        self.review_card = ModernCard(self)
        self.review_card.setVisible(False)
        rev_layout = QVBoxLayout(self.review_card)
        self.lbl_review_title = QLabel("2. Review Detected Clips")
        self.lbl_review_title.setFont(get_system_font(14, QFont.Weight.Bold))
        rev_layout.addWidget(self.lbl_review_title)

        self.table_review = QTableWidget(0, 6)
        self.table_review.setHorizontalHeaderLabels(["Include", "Thumbnail", "Start Time", "End Time", "Duration (s)", "Mini-Preview"])
        self.table_review.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_review.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_review.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_review.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_review.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table_review.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table_review.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_review.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_review.setFixedHeight(220)
        rev_layout.addWidget(self.table_review)

        rev_btns = QHBoxLayout()
        self.btn_play_orig = QPushButton("Play Original Video")
        self.btn_play_orig.clicked.connect(self.play_original)
        rev_btns.addWidget(self.btn_play_orig)

        self.btn_play_res = QPushButton("Play Last Result")
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

        # 6. Real-time Log Textbox & Diagnostics Bar
        self.log_card = ModernCard(self)
        log_layout = QVBoxLayout(self.log_card)
        
        log_header = QHBoxLayout()
        self.lbl_log_title = QLabel("Processing Logs")
        self.lbl_log_title.setFont(get_system_font(11, QFont.Weight.Bold))
        log_header.addWidget(self.lbl_log_title)
        log_header.addStretch()
        
        self.input_log_filter = QLineEdit()
        self.input_log_filter.setPlaceholderText("Filter logs...")
        self.input_log_filter.setFixedWidth(140)
        log_header.addWidget(self.input_log_filter)
        
        self.btn_copy_diag = QPushButton("Copy Diagnostics")
        self.btn_copy_diag.clicked.connect(self.copy_diagnostics)
        log_header.addWidget(self.btn_copy_diag)
        log_layout.addLayout(log_header)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFixedHeight(140)
        self.txt_log.setObjectName("LogConsole")
        self.txt_log.setFont(QFont("Consolas", 10))
        log_layout.addWidget(self.txt_log)
        self.gen_content_layout.addWidget(self.log_card)

        # --- VIEW 1: BETA / CHARACTER GALLERY TAB ---
        self.page_gallery = QWidget()
        gal_layout = QVBoxLayout(self.page_gallery)
        gal_layout.setContentsMargins(0, 0, 0, 0)
        gal_layout.setSpacing(14)
        self.stacked_view.addWidget(self.page_gallery)

        self.gal_top_card = ModernCard(self)
        gt_layout = QVBoxLayout(self.gal_top_card)
        self.lbl_gal_title = QLabel("Face & Character Detection Gallery")
        self.lbl_gal_title.setFont(get_system_font(16, QFont.Weight.Bold))
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
        gal_layout.addWidget(self.gal_top_card)

        # Gallery Grid Scroll Area
        self.scroll_gal = QScrollArea()
        self.scroll_gal.setWidgetResizable(True)
        self.scroll_gal.setFrameShape(QFrame.NoFrame)
        self.gal_grid_container = QWidget()
        self.gal_grid_layout = QGridLayout(self.gal_grid_container)
        self.gal_grid_layout.setSpacing(16)
        self.gal_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
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
        QRadioButton {{
            spacing: 8px;
            background: transparent;
            color: #F8FAFC;
            font-size: 12px;
        }}
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 8px;
            border: 1px solid #3B4457;
            background-color: #1A1E26;
        }}
        QRadioButton::indicator:checked {{
            background-color: {primary};
            border-color: {hover};
        }}
        QLabel#EpisodeBadge {{
            background-color: rgba(37, 99, 235, 0.15);
            border: 1px solid {primary};
            border-radius: 6px;
            padding: 6px 12px;
            font-weight: bold;
            color: #93C5FD;
        }}
        QProgressBar#EpisodeProgressBar {{
            background-color: #1A1E26;
            border: none;
            border-radius: 3px;
        }}
        QProgressBar#EpisodeProgressBar::chunk {{
            background-color: {hover};
            border-radius: 3px;
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
        self.btn_changelog.setText(fix_qt_ampersand(get_translation(lang_name, "changelog")))
        if hasattr(self, "lbl_sys"):
            self.lbl_sys.setText(fix_qt_ampersand(get_translation(lang_name, "sec_system")))
        self.lbl_theme_title.setText(fix_qt_ampersand(get_translation(lang_name, "theme")))
        self.lbl_lang_title.setText(fix_qt_ampersand(get_translation(lang_name, "language")))
        self.chk_sound.setText(fix_qt_ampersand(get_translation(lang_name, "play_sound")))

        self.btn_mode_real.setText(fix_qt_ampersand(get_translation(lang_name, "real_faces")))
        self.btn_mode_anime.setText(fix_qt_ampersand(get_translation(lang_name, "anime")))
        self.btn_tab_gen.setText(fix_qt_ampersand(get_translation(lang_name, "generator_tab")))
        self.btn_tab_gal.setText(fix_qt_ampersand(get_translation(lang_name, "gallery_tab")))

        if hasattr(self, "lbl_hero_title"):
            self.lbl_hero_title.setText(fix_qt_ampersand(get_translation(lang_name, "hero_title")))
        if hasattr(self, "lbl_hero_sub"):
            self.lbl_hero_sub.setText(fix_qt_ampersand(get_translation(lang_name, "hero_subtitle")))
        if hasattr(self, "lbl_presets_title"):
            self.lbl_presets_title.setText(fix_qt_ampersand(get_translation(lang_name, "preset_label")))
        if hasattr(self, "btn_autotune"):
            self.btn_autotune.setText(fix_qt_ampersand(get_translation(lang_name, "btn_auto_tune")))
        if hasattr(self, "lbl_aspect_title"):
            self.lbl_aspect_title.setText(fix_qt_ampersand(get_translation(lang_name, "aspect_label")))
        if hasattr(self, "lbl_pad_before"):
            self.lbl_pad_before.setText(fix_qt_ampersand(get_translation(lang_name, "pad_before")))
        if hasattr(self, "lbl_pad_after"):
            self.lbl_pad_after.setText(fix_qt_ampersand(get_translation(lang_name, "pad_after")))
        if hasattr(self, "lbl_max_gap"):
            self.lbl_max_gap.setText(fix_qt_ampersand(get_translation(lang_name, "max_gap")))
        if hasattr(self, "lbl_min_scene"):
            self.lbl_min_scene.setText(fix_qt_ampersand(get_translation(lang_name, "min_scene")))
        if hasattr(self, "lbl_frame_skip"):
            self.lbl_frame_skip.setText(fix_qt_ampersand(get_translation(lang_name, "frame_skip")))
        if hasattr(self, "chk_vad"):
            self.chk_vad.setText(fix_qt_ampersand(get_translation(lang_name, "vad_enable")))
        if hasattr(self, "lbl_vad_buf"):
            self.lbl_vad_buf.setText(fix_qt_ampersand(get_translation(lang_name, "vad_buffer")))
        if hasattr(self, "chk_speaker"):
            self.chk_speaker.setText(fix_qt_ampersand(get_translation(lang_name, "vad_speaker_enable")))
        if hasattr(self, "lbl_speaker_thresh"):
            self.lbl_speaker_thresh.setText(fix_qt_ampersand(get_translation(lang_name, "vad_speaker_threshold")))
        if hasattr(self, "btn_select_video"):
            self.btn_select_video.setText(fix_qt_ampersand(get_translation(lang_name, "sel_video")))
        if hasattr(self, "btn_select_image"):
            self.btn_select_image.setText(fix_qt_ampersand(get_translation(lang_name, "sel_ref")))
        if hasattr(self, "btn_select_output"):
            self.btn_select_output.setText(fix_qt_ampersand(get_translation(lang_name, "sel_output")))
        if hasattr(self, "btn_generate"):
            self.btn_generate.setText(fix_qt_ampersand(get_translation(lang_name, "generate")))
        if hasattr(self, "lbl_review_title"):
            self.lbl_review_title.setText(fix_qt_ampersand(get_translation(lang_name, "review_title")))
        if hasattr(self, "btn_render"):
            self.btn_render.setText(fix_qt_ampersand(get_translation(lang_name, "btn_render")))
        if hasattr(self, "lbl_log_title"):
            self.lbl_log_title.setText(fix_qt_ampersand(get_translation(lang_name, "logs_title")))
        if hasattr(self, "lbl_gal_title"):
            self.lbl_gal_title.setText(fix_qt_ampersand(get_translation(lang_name, "gallery_title")))
        if hasattr(self, "lbl_gal_sub"):
            self.lbl_gal_sub.setText(fix_qt_ampersand(get_translation(lang_name, "gallery_desc")))
        if hasattr(self, "btn_gal_scan"):
            self.btn_gal_scan.setText(fix_qt_ampersand(get_translation(lang_name, "scan_chars")))
        if hasattr(self, "btn_gal_cancel"):
            self.btn_gal_cancel.setText(fix_qt_ampersand(get_translation(lang_name, "btn_cancel_gallery")))

        if hasattr(self, "btn_play_orig"):
            self.btn_play_orig.setText(get_translation(lang_name, "play_orig"))
        if hasattr(self, "btn_play_res"):
            self.btn_play_res.setText(get_translation(lang_name, "play_result"))
        if hasattr(self, "table_review"):
            self.table_review.setHorizontalHeaderLabels([
                get_translation(lang_name, "th_include"),
                get_translation(lang_name, "th_thumb"),
                get_translation(lang_name, "th_start"),
                get_translation(lang_name, "th_end"),
                get_translation(lang_name, "th_duration")
            ])

        if hasattr(self, "combo_presets"):
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

        if hasattr(self, "combo_aspect"):
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
        try:
            dlg = QDialog(self)
            dlg.setWindowTitle(f"{get_translation(self.current_lang, 'changelog_title')} ({APP_VERSION})")
            dlg.resize(750, 550)
            dlg.setStyleSheet("background-color: #14161B; color: #FFFFFF;")
            layout = QVBoxLayout(dlg)

            title_lbl = QLabel(f"Focus - Changelog ({get_translation(self.current_lang, 'changelog_title')})")
            title_lbl.setFont(get_system_font(16, QFont.Weight.Bold))
            layout.addWidget(title_lbl)

            txt = QTextEdit()
            txt.setReadOnly(True)
            txt.setFont(get_system_font(10))
            txt.setStyleSheet("background-color: #1A1D24; color: #E0E0E0; border: 1px solid #2D3139; border-radius: 8px; padding: 10px;")

            msg = get_changelog_text(self.current_lang)
            txt.setText(msg)
            layout.addWidget(txt)

            close_label = get_translation(self.current_lang, "changelog_close")
            btn_close = QPushButton(close_label if close_label else "Close")
            btn_close.setStyleSheet("background-color: #2D3139; color: #FFFFFF; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
            btn_close.clicked.connect(dlg.accept)
            layout.addWidget(btn_close, 0, Qt.AlignmentFlag.AlignCenter)

            dlg.exec()
        except Exception as e:
            logging.error(f"Failed to open Changelog dialog: {e}")
            QMessageBox.information(self, "Changelog", get_changelog_text(self.current_lang))


    def get_input_video_paths(self) -> List[Path]:
        return parse_video_paths(self.video_path_str)

    def has_valid_video_input(self) -> bool:
        paths = self.get_input_video_paths()
        return len(paths) > 0 and any(p.is_file() for p in paths)

    def set_selected_video_files(self, paths: List[str]):
        if not paths:
            return
        
        valid_paths = [p for p in paths if p and os.path.isfile(p)]
        if not valid_paths:
            QMessageBox.warning(self, "No Valid Videos", "None of the selected video files exist on disk.")
            return

        valid_paths = sorted(list(dict.fromkeys(valid_paths)), key=natural_sort_key)

        self.batch_queue_files.clear()
        if hasattr(self, 'list_batch_queue'):
            self.list_batch_queue.clear()
        for p in valid_paths:
            self.batch_queue_files.append(p)
            if hasattr(self, 'list_batch_queue'):
                self.list_batch_queue.addItem(Path(p).name)

        if len(valid_paths) == 1:
            self.video_path_str = valid_paths[0]
            self.lbl_video_path.setText(f"🎬 {Path(valid_paths[0]).name}")
            if hasattr(self, 'lbl_batch_status'):
                self.lbl_batch_status.setText("Batch Processing Queue (1 file ready)")
        else:
            self.video_path_str = ";".join(valid_paths)
            names = [Path(p).name for p in valid_paths]
            if len(names) <= 2:
                display_txt = f"🎬 {len(valid_paths)} Videos Selected ({', '.join(names)})"
            else:
                display_txt = f"🎬 {len(valid_paths)} Videos Selected ({names[0]}, {names[1]}... +{len(names)-2} more)"
            self.lbl_video_path.setText(display_txt)
            if hasattr(self, 'lbl_batch_status'):
                self.lbl_batch_status.setText(f"Batch Processing Queue ({len(valid_paths)} file(s) ready in order S01->S02)")

        self.apply_auto_tune()
        
        self.audio_worker = AudioTrackWorker(ScenePackGenerator, valid_paths[0], self.current_mode, self.queue_proxy)
        self.audio_worker.start()

    def select_video(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Input Video(s)", "", "Video Files (*.mp4 *.mkv *.mov *.avi *.webm *.flv *.m4v *.ts);;All Files (*.*)")
        if paths:
            self.set_selected_video_files(paths)

    def add_folder_videos(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing Video Files")
        if folder:
            video_exts = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".m4v", ".ts"}
            folder_path = Path(folder)
            found_files = []
            for file_path in folder_path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in video_exts:
                    found_files.append(str(file_path.resolve()))
            
            if found_files:
                found_files = sorted(list(dict.fromkeys(found_files)), key=natural_sort_key)
                self.set_selected_video_files(found_files)
                self.toast.show_toast(f"Added {len(found_files)} video(s) from folder to queue (sorted S01->S02)!", "📁", 4000)
            else:
                QMessageBox.information(self, "No Videos Found", f"No supported video files were found in:\n{folder}")

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
        valid_paths = self.get_input_video_paths()
        if valid_paths and valid_paths[0].is_file():
            try:
                cap = cv2.VideoCapture(str(valid_paths[0]))
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
        valid_paths = self.get_input_video_paths()
        if not valid_paths:
            QMessageBox.warning(self, "Missing Files", "Please select valid Input Video(s).")
            return

        if (self.is_batch_running or len(valid_paths) > 1) and not self.output_path_str:
            v_name = valid_paths[0].stem if len(valid_paths) == 1 else "Master_MultiVideo"
            out_dir = Path.home() / "Desktop"
            self.output_path_str = str(out_dir / f"{v_name}_scenepack.mp4")
            self.lbl_output_path.setText(Path(self.output_path_str).name)

        if not self.has_valid_video_input() or not self.output_path_str:
            QMessageBox.warning(self, "Missing Files", "Please select both valid Input Video(s) and Save Location.")
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
            QMessageBox.critical(self, "Invalid Input", "Numeric parameters must be valid numbers.")
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
        if not self.has_valid_video_input():
            QMessageBox.warning(self, "No Input Video", "Please select valid input video file(s) before rendering!")
            return

        selected_intervals = []
        for (interval, chk) in self.review_checkboxes:
            if chk.isChecked():
                selected_intervals.append(interval)

        if not selected_intervals:
            if self.is_batch_running:
                logging.warning(f"Batch item {self.current_batch_index + 1}: No clips selected for render.")
                self.current_batch_index += 1
                QTimer.singleShot(500, self._process_next_batch_item)
                return
            else:
                QMessageBox.warning(self, "No Clips Selected", "Please select at least one clip in the table to render.")
                return

        if not self.output_path_str:
            path, _ = QFileDialog.getSaveFileName(self, "Select Save Location", "scenepack.mp4", "MP4 Video (*.mp4);;All Files (*.*)")
            if path:
                self.output_path_str = path
                self.lbl_output_path.setText(Path(path).name)
            else:
                QMessageBox.warning(self, "No Save Location", "Please select an output save file location before rendering.")
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
        
        audio_track_idx = self.combo_audio_track.currentData()
        if audio_track_idx is None:
            audio_track_idx = 0

        generator_inst = getattr(self.scan_worker, "generator_instance", None) if self.scan_worker else ScenePackGenerator(log_queue=self.queue_proxy, mode=self.current_mode)
        export_quality = self.combo_export_quality.currentText()
        self.render_worker = RenderWorker(
            generator_inst, self.video_path_str, selected_intervals,
            self.output_path_str, aspect_canonical, self.queue_proxy,
            audio_track_index=audio_track_idx,
            export_quality=export_quality
        )
        self.render_worker.start()

    def start_gallery_scan(self):
        valid_paths = self.get_input_video_paths()
        if not valid_paths or not valid_paths[0].is_file():
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
        valid_paths = self.get_input_video_paths()
        if valid_paths and valid_paths[0].is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(valid_paths[0])))

    # --- SIGNAL SLOTS ---
    @Slot(str)
    def _on_log_msg(self, msg: str):
        self.txt_log.append(msg)
        # Auto scroll to bottom
        scrollbar = self.txt_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @Slot(float, str)
    def _on_progress_update(self, val: float, status: str):
        target = int(val * 1000)
        self._animate_progress(self.progress_bar, target)
        self.lbl_eta.setText(status)

    @Slot(int, int, str, float, float)
    def _on_episode_progress(self, cur_ep: int, tot_eps: int, ep_name: str, ep_prog: float, tot_prog: float):
        if hasattr(self, 'lbl_episode_badge'):
            self.lbl_episode_badge.setVisible(True)
            self.lbl_episode_badge.setText(f"🎬 Episode [{cur_ep}/{tot_eps}]: {ep_name} ({int(ep_prog*100)}%)")
        if hasattr(self, 'episode_progress_bar'):
            self.episode_progress_bar.setVisible(True)
            self._animate_progress(self.episode_progress_bar, int(ep_prog * 1000))
        target_tot = int(tot_prog * 1000)
        self._animate_progress(self.progress_bar, target_tot)

    @Slot(float, str)
    def _on_gallery_progress(self, val: float, status: str):
        target = int(val * 1000)
        self._animate_progress(self.gal_progress_bar, target)
        self.lbl_gal_status.setText(status)

    def _animate_progress(self, bar: QProgressBar, target_val: int):
        cur = bar.value()
        if abs(cur - target_val) < 3:
            bar.setValue(target_val)
            return
        anim = QPropertyAnimation(bar, b"value", self)
        anim.setDuration(220)
        anim.setStartValue(cur)
        anim.setEndValue(target_val)
        anim.setEasingCurve(QEasingCurve.OutQuad)
        anim.start()

    def _apply_smart_preset(self, preset_type: str):
        if preset_type == "tiktok":
            self.combo_aspect.setCurrentText("9:16 Vertical")
            self.input_pad_before.setText("1.5")
            self.input_pad_after.setText("1.5")
            self.input_min_scene.setText("1.0")
            self.input_frame_skip.setText("12")
            self.toast.show_toast("Applied Preset: 📱 TikTok / Shorts (9:16 Vertical)", "📱")
        elif preset_type == "youtube":
            self.combo_aspect.setCurrentText("16:9 Original")
            self.input_pad_before.setText("2.0")
            self.input_pad_after.setText("2.0")
            self.input_min_scene.setText("1.5")
            self.input_frame_skip.setText("15")
            self.toast.show_toast("Applied Preset: 🎬 YouTube Scenepack (16:9)", "🎬")
        elif preset_type == "draft":
            self.combo_aspect.setCurrentText("16:9 Original")
            self.input_pad_before.setText("1.0")
            self.input_pad_after.setText("1.0")
            self.input_min_scene.setText("0.8")
            self.input_frame_skip.setText("30")
            self.toast.show_toast("Applied Preset: ⚡ Ultra-Fast Draft Scan", "⚡")
        self.save_current_settings()

    def add_batch_videos(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Multiple Video Files for Batch Queue", "",
            "Video Files (*.mp4 *.mkv *.mov *.avi *.webm *.flv *.m4v *.ts);;All Files (*.*)"
        )
        if paths:
            self.set_selected_video_files(paths)

    def clear_batch_queue(self):
        self.batch_queue_files.clear()
        if hasattr(self, 'list_batch_queue'):
            self.list_batch_queue.clear()
        self.video_path_str = ""
        self.lbl_video_path.setText("No video selected")
        if hasattr(self, 'lbl_batch_status'):
            self.lbl_batch_status.setText("Batch Queue: Empty")
        if hasattr(self, 'lbl_episode_badge'):
            self.lbl_episode_badge.setVisible(False)
        if hasattr(self, 'episode_progress_bar'):
            self.episode_progress_bar.setVisible(False)
        self.combo_audio_track.clear()
        self.combo_audio_track.addItem("Default Audio Stream (Track 1)", 0)
        self.toast.show_toast("Video selection cleared", "🗑️")

    def start_batch_processing(self):
        if not self.batch_queue_files:
            QMessageBox.information(self, "Batch Queue Empty", "Please add video files to the batch queue first.")
            return
        if not hasattr(self, 'image_path_str') or (not self.image_path_str and self.selected_ref_data is None):
            QMessageBox.warning(self, "Missing Reference Face", "Please select a reference face image before processing the batch queue.")
            return
        
        if self.radio_batch_single.isChecked():
            self.video_path_str = ";".join(self.batch_queue_files)
            self.start_scan()
            return

        self.btn_run_batch.setEnabled(False)
        self.btn_generate.setEnabled(False)
        self.is_batch_running = True
        self.batch_rendered_outputs = []
        self.current_batch_index = 0
        self._process_next_batch_item()

    def _process_next_batch_item(self):
        if not self.is_batch_running:
            self.btn_run_batch.setEnabled(True)
            self.btn_generate.setEnabled(True)
            return

        if self.current_batch_index < len(self.batch_queue_files):
            v_path = self.batch_queue_files[self.current_batch_index]
            self.video_path_str = v_path
            self.lbl_video_path.setText(Path(v_path).name)
            self.lbl_batch_status.setText(f"Processing Batch Item {self.current_batch_index + 1} of {len(self.batch_queue_files)}: {Path(v_path).name}")
            self.toast.show_toast(f"Batch [{self.current_batch_index + 1}/{len(self.batch_queue_files)}]: Scanning {Path(v_path).name}")
            
            # Reset audio tracks for current batch file
            self.combo_audio_track.clear()
            self.combo_audio_track.addItem("Default Audio Stream (Track 1)", 0)

            self.start_scan()
        else:
            self.is_batch_running = False
            self.btn_run_batch.setEnabled(True)
            self.btn_generate.setEnabled(True)

            valid_rendered = [p for p in self.batch_rendered_outputs if os.path.exists(p)]
            
            if self.radio_batch_single.isChecked():
                if len(valid_rendered) > 1:
                    self._concatenate_master_scenepack()
                elif len(valid_rendered) == 1:
                    out_dir = Path(self.output_path_str).parent if self.output_path_str else Path.home() / "Desktop"
                    master_out = out_dir / "Master_Consolidated_Scenepack.mp4"
                    try:
                        shutil.copy2(valid_rendered[0], master_out)
                        self.lbl_batch_status.setText(f"Master Scenepack Created: {master_out.name}")
                        self.toast.show_toast("Batch Processing Complete!", "Success", 4000)
                    except Exception as e:
                        logging.error(f"Copying single master scenepack failed: {e}")
                        self.lbl_batch_status.setText("Batch Processing Complete!")
                else:
                    self.lbl_batch_status.setText("Batch Processing Complete (No clips rendered).")
                    self.toast.show_toast("Batch ended with 0 clips rendered.", "Warning", 4000)
            else:
                self.lbl_batch_status.setText("Batch Processing Complete!")
                self.toast.show_toast(f"Batch complete: Rendered {len(valid_rendered)} file(s).", "Success", 4000)

    def _concatenate_master_scenepack(self):
        try:
            out_dir = Path(self.output_path_str).parent if self.output_path_str else Path.home() / "Desktop"
            master_out = out_dir / "Master_Consolidated_Scenepack.mp4"
            valid_paths = [Path(p) for p in self.batch_rendered_outputs if os.path.exists(p)]
            if valid_paths:
                self.lbl_batch_status.setText("Creating Master Scenepack in background...")
                self.master_concat_worker = MasterConcatWorker(sg_engine, valid_paths, master_out, self.queue_proxy)
                self.master_concat_worker.start()
            else:
                self.btn_run_batch.setEnabled(True)
                QMessageBox.warning(self, "Master Scenepack Error", "No valid rendered outputs found to concatenate. Make sure you have successfully rendered clips first.")
        except Exception as e:
            self.btn_run_batch.setEnabled(True)
            logging.error(f"Master concatenation failed: {e}")

    @Slot(str)
    def _on_master_concat_complete(self, master_out: str):
        self.btn_run_batch.setEnabled(True)
        if master_out:
            master_out_path = Path(master_out)
            self.lbl_batch_status.setText(f"Master Scenepack Created: {master_out_path.name}")
            self.toast.show_toast(f"Master Scenepack Created: {master_out_path.name}", duration_ms=4000)
            QMessageBox.information(self, "Master Scenepack Complete", f"Consolidated Master Scenepack saved to:\n{master_out_path}")
        else:
            self.lbl_batch_status.setText("Master Scenepack Creation Failed.")

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
            c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            c_layout.setSpacing(8)

            img_label = QLabel()
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            crop_path = cluster.get("crop_path")
            if crop_path and os.path.exists(crop_path):
                pixmap = QPixmap(crop_path).scaled(110, 110, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                img_label.setPixmap(pixmap)
            else:
                img_label.setText("No Image")
            c_layout.addWidget(img_label)

            name_str = f"Character #{cluster['id']}"
            cnt_str = f"{cluster['count']} detection(s)"
            lbl_name = QLabel(f"<b>{name_str}</b> ({cnt_str})")
            lbl_name.setFont(get_system_font(11, QFont.Weight.Bold))
            lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            c_layout.addWidget(lbl_name)

            lbl_count = QLabel(f"{cluster['count']} detection(s)")
            lbl_count.setObjectName("SubText")
            lbl_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        if hasattr(self, 'lbl_episode_badge'):
            self.lbl_episode_badge.setVisible(False)
        if hasattr(self, 'episode_progress_bar'):
            self.episode_progress_bar.setVisible(False)

        self.scanned_intervals = intervals
        self.review_checkboxes = []
        self.table_review.setRowCount(len(intervals))
        self.table_review.setRowHeight(0, 95)

        for idx, item in enumerate(intervals):
            if len(item) >= 4 and isinstance(item[0], (str, Path)):
                v_src = str(item[0])
                start, end = float(item[1]), float(item[2])
                avg_x = float(item[3])
            else:
                v_src = self.video_path_str
                start, end = float(item[0]), float(item[1])
                avg_x = float(item[2]) if len(item) > 2 else 0.5

            self.table_review.setRowHeight(idx, 95)

            # Col 0: Checkbox
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            chk = QCheckBox()
            chk.setChecked(True)
            chk_layout.addWidget(chk)
            self.table_review.setCellWidget(idx, 0, chk_widget)
            self.review_checkboxes.append((item, chk))

            # Col 1: Thumbnail
            thumb_label = QLabel()
            thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if idx < len(thumbnails) and thumbnails[idx] is not None:
                pil_img = thumbnails[idx]
                data = pil_img.convert("RGBA").tobytes("raw", "RGBA")
                qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_RGBA8888)
                pixmap = QPixmap.fromImage(qimg)
                thumb_label.setPixmap(pixmap)
            else:
                thumb_label.setText("No Thumb")
            self.table_review.setCellWidget(idx, 1, thumb_label)

            # Col 2, 3, 4: Times
            item_start = QTableWidgetItem(f"{start:.2f}s")
            item_start.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if len(item) >= 4:
                item_start.setToolTip(f"Source File: {Path(v_src).name}")
            self.table_review.setItem(idx, 2, item_start)

            item_end = QTableWidgetItem(f"{end:.2f}s")
            item_end.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_review.setItem(idx, 3, item_end)

            item_dur = QTableWidgetItem(f"{end - start:.2f}s")
            item_dur.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_review.setItem(idx, 4, item_dur)

            # Col 5: Mini-Preview Button
            btn_prev = QPushButton("▶️ Preview")
            btn_prev.setFixedWidth(85)
            btn_prev.clicked.connect(lambda chk=False, src=v_src, s=start, e=end: self._open_mini_preview(s, e, src_video=src))
            self.table_review.setCellWidget(idx, 5, btn_prev)

        self.review_card.setVisible(True)
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText(get_translation(self.current_lang, "generate"))
        self.lbl_eta.setText(f"Scan complete! Review {len(intervals)} clip(s) below and click Render.")

        if self.is_batch_running:
            if not intervals:
                logging.info(f"Batch item {self.current_batch_index + 1} yielded 0 clips. Skipping to next batch item...")
                self.lbl_batch_status.setText(f"Item {self.current_batch_index + 1} yielded 0 clips. Moving to next...")
                self.toast.show_toast(f"No clips found in item {self.current_batch_index + 1}, skipping...", "Info", 3000)
                self.current_batch_index += 1
                QTimer.singleShot(500, self._process_next_batch_item)
                return

            out_dir = Path(self.output_path_str).parent if self.output_path_str else Path.home() / "Desktop"
            v_name = Path(self.video_path_str).stem
            auto_out_path = out_dir / f"{v_name}_scenepack.mp4"
            self.output_path_str = str(auto_out_path)
            self.lbl_output_path.setText(auto_out_path.name)
            QTimer.singleShot(800, self.start_render)

    def _open_mini_preview(self, start_sec: float, end_sec: float, src_video: Optional[str] = None):
        target_video = src_video if src_video and os.path.exists(src_video) else self.video_path_str
        if not target_video or not os.path.exists(target_video):
            QMessageBox.warning(self, "No Video", "Video file unavailable for preview.")
            return
        dlg = MiniPreviewDialog(self, target_video, start_sec, end_sec)
        dlg.exec()

    def copy_diagnostics(self):
        diag_text = (
            f"=== FOCUS DIAGNOSTIC REPORT ({APP_VERSION}) ===\n"
            f"OS: {sys.platform} ({platform.platform()})\n"
            f"Python: {sys.version}\n"
            f"CPU Cores: {os.cpu_count()}\n"
            f"Log Console Output:\n"
            f"{self.txt_log.toPlainText()}\n"
        )
        clipboard = QApplication.clipboard()
        clipboard.setText(diag_text)
        if hasattr(self, 'toast'):
            self.toast.show_toast("Diagnostics copied to clipboard!", "📋")

    @Slot(str)
    def _on_render_complete(self, out_path: str):
        self.btn_render.setEnabled(True)
        self.btn_render.setText(get_translation(self.current_lang, "btn_render"))
        self.progress_bar.setValue(1000)
        self.lbl_eta.setText(f"Rendering complete! Saved to: {Path(out_path).name}")
        if self.chk_sound.isChecked():
            QApplication.beep()
        if not self.is_batch_running:
            QMessageBox.information(self, "Success", f"Scenepack successfully rendered and saved to:\n{out_path}")
        else:
            if hasattr(self, 'batch_rendered_outputs'):
                self.batch_rendered_outputs.append(out_path)
            self.current_batch_index += 1
            QTimer.singleShot(1000, self._process_next_batch_item)

    @Slot(str)
    def _on_error_msg(self, err: str):
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText(get_translation(self.current_lang, "generate"))
        self.btn_render.setEnabled(True)
        self.btn_render.setText(get_translation(self.current_lang, "btn_render"))

        if self.is_batch_running:
            logging.error(f"Batch processing error on item {self.current_batch_index + 1}: {err}")
            self.lbl_batch_status.setText(f"Error on item {self.current_batch_index + 1}. Continuing batch...")
            self.toast.show_toast(f"Batch item {self.current_batch_index + 1} failed, skipping...", "Error", 4000)
            self.current_batch_index += 1
            QTimer.singleShot(1000, self._process_next_batch_item)
            return

        log_dir = get_app_dir()
        log_path = log_dir / "focus_debug.log"
        
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Execution Error")
        msg_box.setText(f"An error occurred during processing:\n{err}\n\nDetailed diagnostic log saved to:\n{log_path}")
        btn_open = msg_box.addButton("Open Log Folder", QMessageBox.ButtonRole.ActionRole)
        msg_box.addButton(QMessageBox.StandardButton.Ok)
        msg_box.exec()
        
        if msg_box.clickedButton() == btn_open:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_dir)))

    @Slot()
    def _on_reset_buttons(self):
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText(get_translation(self.current_lang, "generate"))
        self.btn_render.setEnabled(True)
        self.btn_render.setText(get_translation(self.current_lang, "btn_render"))

    def closeEvent(self, event):
        logging.info("Shutting down Focus GUI...")
        self.save_current_settings()
        workers = [
            getattr(self, 'gallery_worker', None),
            getattr(self, 'scan_worker', None),
            getattr(self, 'render_worker', None),
            getattr(self, 'audio_worker', None),
            getattr(self, 'master_concat_worker', None)
        ]
        for w in workers:
            if w and w.isRunning():
                if hasattr(w, 'cancel'):
                    try:
                        w.cancel()
                    except Exception:
                        pass
                w.quit()
                w.wait(1500)

        try:
            gen = ScenePackGenerator()
            gen.terminate_all_subprocesses()
        except Exception:
            pass
        gc.collect()
        event.accept()

class FocusSplashScreen(QSplashScreen):
    """
    Modern Dark Studio Splash Screen.
    Instantly gives visual feedback while heavy AI & PySide6 components load.
    """
    def __init__(self, pixmap_size=(520, 280)):
        pix = QPixmap(pixmap_size[0], pixmap_size[1])
        pix.fill(QColor("#14161B"))

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(0, 0, pixmap_size[0], pixmap_size[1])
        painter.setPen(QPen(QColor("#2C2F36"), 2))
        painter.setBrush(QColor("#14161B"))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 16, 16)

        font_title = get_system_font(32, QFont.Weight.Bold)
        painter.setFont(font_title)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(QRectF(0, 70, pixmap_size[0], 50), Qt.AlignmentFlag.AlignCenter, "FOCUS")

        font_sub = get_system_font(12)
        painter.setFont(font_sub)
        painter.setPen(QColor("#8A8F9E"))
        painter.drawText(QRectF(35, 105, 450, 25), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"AI Scenepack Generator ({APP_VERSION})")

        painter.setBrush(QColor("#8B5CF6"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(35, 145, 160, 5), 3, 3)

        painter.end()

        super().__init__(pix, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)


def main():
    if sys.platform == "darwin":
        try:
            exe_path = os.path.abspath(sys.executable)
            if ".app/Contents" in exe_path:
                bundle_root = exe_path.split(".app/Contents")[0] + ".app"
                subprocess.run(["xattr", "-cr", bundle_root], capture_output=True)
                subprocess.run(["xattr", "-dr", "com.apple.quarantine", bundle_root], capture_output=True)
        except Exception:
            pass

    if sys.platform == "win32":
        try:
            import ctypes
            myappid = 'bartosz55dev.focus.ai'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(get_application_icon())
    app.setQuitOnLastWindowClosed(False)

    # 1. Instant Startup Splash Screen
    splash = FocusSplashScreen()
    splash.show()
    splash.showMessage("   🚀 Initializing Focus AI Scenepack Studio...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, QColor("#9CA3AF"))
    app.processEvents()

    # 2. Load Main Window
    window = FocusApp()
    splash.showMessage("   ✨ Loading AI Vision Models & Hardware Encoders...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, QColor("#9CA3AF"))
    app.processEvents()

    window.show()
    window.raise_()
    window.activateWindow()

    if sys.platform == "darwin":
        def _force_macos_focus():
            window.show()
            window.raise_()
            window.activateWindow()
        QTimer.singleShot(100, _force_macos_focus)
        QTimer.singleShot(500, _force_macos_focus)

    splash.finish(window)
    app.setQuitOnLastWindowClosed(True)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
