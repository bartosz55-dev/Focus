import sys
import os
import subprocess
from pathlib import Path
import tempfile
import shutil
import logging
import threading
import queue
import time
import platform
from typing import List, Tuple, Any, Optional, Dict, Union, Set, Callable
import json
import numpy as np
from PIL import Image, ImageDraw
try:
    from PIL import ImageTk
except ImportError:
    ImageTk = None
try:
    import tkinter as tk
except ImportError:
    tk = None
try:
    from tkinter import filedialog, messagebox
except ImportError:
    filedialog = None
    messagebox = None
try:
    import customtkinter as ctk
except ImportError:
    ctk = None

from scenepack_generator_backend import (
    APP_VERSION,
    CASCADE_DOWNLOAD_LOCK,
    CREATE_NO_WINDOW,
    PlatformManager,
    ScenePackGenerator,
    write_concat_list,
    canonicalize_mode,
    make_square_crop,
    extract_anime_face_features,
    is_anime_feature_match,
    TRANSLATIONS,
    get_app_dir,
    get_translation,
    get_changelog_text,
    TextboxLogHandler,
)

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

try:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox
except ImportError:
    ctk = None
    filedialog = None
    messagebox = None

# Custom Logging Handler to forward logs to our GUI Queue

class FocusApp(ctk.CTk if ctk else object):
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

        self.app_dir = get_app_dir()
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

        history_text = get_changelog_text(lang_name)

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
                    import ssl
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, context=ctx) as response, open(self.anime_cascade_path, 'wb') as out_file:
                        shutil.copyfileobj(response, out_file)
                        
                    if self.anime_cascade_path.stat().st_size < 50000:
                        try:
                            self.anime_cascade_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                        err_msg = "Downloaded file size is under 50KB; download was likely blocked or corrupted."
                        self.log_queue.put(("log", err_msg))
                        self.log_queue.put(("gallery_error", err_msg))
                        return
                        
                    self.log_queue.put(("log", "Successfully downloaded anime face cascade model."))
                except Exception as e:
                    try:
                        self.anime_cascade_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    err_msg = f"Failed to download anime cascade model: {e}"
                    self.log_queue.put(("log", err_msg))
                    self.log_queue.put(("gallery_error", err_msg))
                    return

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
        if hasattr(self, 'generator') and self.generator:
            self.generator.terminate_all_subprocesses()

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
                    cascade = sg_engine.get_cascade_classifier(str(self.anime_cascade_path))
                    if cascade is None or (hasattr(cascade, 'empty') and cascade.empty()):
                        err_msg = "Failed to load anime cascade classifier XML model."
                        logging.error(err_msg)
                        self.log_queue.put(("log", err_msg))
                        self.log_queue.put(("gallery_error", err_msg))
                        return
                elif mode == "Real Faces":
                    profile_cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_profileface.xml')
                    profile_cascade = sg_engine.get_cascade_classifier(profile_cascade_path)
    
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
            self.generator.extract_and_concat(Path(v_path), intervals, Path(o_path), aspect_ratio, export_quality="Medium (CRF 20)")
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
