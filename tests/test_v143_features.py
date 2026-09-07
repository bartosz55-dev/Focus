import unittest
import os
import sys
import tempfile
import json
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication(sys.argv)

import scenepack_generator_backend as backend
import scenepack_generator_gui_qt as gui_qt


class TestFocusV143Features(unittest.TestCase):
    """Test suite verifying all v1.43 features and bugfixes."""

    def test_version_bump(self):
        """Verify APP_VERSION is updated to v2.0.0 across backend and GUI."""
        self.assertEqual(backend.APP_VERSION, "v2.0.0")
        self.assertEqual(gui_qt.APP_VERSION, "v2.0.0")

    def test_sidebar_logo_no_emoji(self):
        """Verify the 🎯 emoji has been removed from the logo header."""
        window = gui_qt.FocusApp()
        try:
            self.assertEqual(window.lbl_logo.text(), "FOCUS")
            self.assertFalse(hasattr(window, "lbl_logo_icon"))
        finally:
            window.close()

    def test_mode_buttons_not_truncated(self):
        """Verify mode switcher buttons have adequate minimum width and expanding policy."""
        window = gui_qt.FocusApp()
        try:
            self.assertGreaterEqual(window.btn_mode_anime.minimumWidth(), 160)
            self.assertGreaterEqual(window.btn_mode_real.minimumWidth(), 160)
            self.assertIn("QPushButton#ModeBtn", window.styleSheet())
        finally:
            window.close()

    def test_no_ampersand_mnemonic_in_scan_button(self):
        """Verify the scan button text and translation key do not use unescaped single &."""
        trans_en = backend.get_translation("English", "scanning_analyzing")
        self.assertNotIn(" & ", trans_en)
        self.assertIn("and", trans_en.lower())

        trans_pl = backend.get_translation("Polski", "scanning_analyzing")
        self.assertNotIn(" & ", trans_pl)
        self.assertIn("i", trans_pl.lower())

    def test_review_bulk_selection_buttons(self):
        """Verify Select All and Deselect All buttons toggle checkboxes properly."""
        window = gui_qt.FocusApp()
        try:
            self.assertTrue(hasattr(window, "btn_select_all"))
            self.assertTrue(hasattr(window, "btn_deselect_all"))
            self.assertTrue(hasattr(window, "chk_auto_render"))

            # Simulate 3 items in review checkboxes
            from PySide6.QtWidgets import QCheckBox
            cb1, cb2, cb3 = QCheckBox(), QCheckBox(), QCheckBox()
            cb1.setChecked(True)
            cb2.setChecked(False)
            cb3.setChecked(True)
            window.review_checkboxes = [
                ((0, 5, 0.5), cb1),
                ((5, 10, 0.5), cb2),
                ((10, 15, 0.5), cb3),
            ]

            # Deselect all
            window._set_all_review_clips(False)
            self.assertFalse(cb1.isChecked())
            self.assertFalse(cb2.isChecked())
            self.assertFalse(cb3.isChecked())

            # Select all
            window._set_all_review_clips(True)
            self.assertTrue(cb1.isChecked())
            self.assertTrue(cb2.isChecked())
            self.assertTrue(cb3.isChecked())
        finally:
            window.close()

    def test_sleep_inhibitor_lifecycle(self):
        """Verify SleepInhibitor activates and deactivates without crashing."""
        backend.SleepInhibitor.prevent_sleep()
        if sys.platform == "darwin":
            self.assertIsNotNone(backend.SleepInhibitor._caffeinate_proc)
        backend.SleepInhibitor.allow_sleep()
        if sys.platform == "darwin":
            self.assertIsNone(backend.SleepInhibitor._caffeinate_proc)

    def test_preset_manager_crud(self):
        """Verify PresetManager saves, loads, and deletes presets correctly."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_preset_file = Path(tf.name)

        orig_file = backend.PresetManager.PRESETS_FILE
        try:
            backend.PresetManager.PRESETS_FILE = temp_preset_file

            # 1. Initial state
            presets = backend.PresetManager.load_presets()
            self.assertEqual(presets, {})

            # 2. Save custom preset
            sample_data = {
                "pad_before": 1.5,
                "pad_after": 2.0,
                "frame_skip": 10,
                "aspect": "9:16 Vertical"
            }
            res = backend.PresetManager.save_preset("ActionAnime", sample_data)
            self.assertTrue(res)

            # 3. Load preset
            presets = backend.PresetManager.load_presets()
            self.assertIn("ActionAnime", presets)
            self.assertEqual(presets["ActionAnime"]["pad_before"], 1.5)

            # 4. Delete preset
            res_del = backend.PresetManager.delete_preset("ActionAnime")
            self.assertTrue(res_del)
            presets_after = backend.PresetManager.load_presets()
            self.assertNotIn("ActionAnime", presets_after)
        finally:
            backend.PresetManager.PRESETS_FILE = orig_file
            if temp_preset_file.exists():
                temp_preset_file.unlink()

    def test_application_icons_exist_and_load(self):
        """Verify icon.ico, icon.png, and icon.icns exist and get_application_icon loads valid icon."""
        base_dir = Path(__file__).parent.parent
        icon_ico = base_dir / "icon.ico"
        icon_png = base_dir / "icon.png"
        icon_icns = base_dir / "icon.icns"

        self.assertTrue(icon_png.exists(), "icon.png must exist")
        self.assertTrue(icon_ico.exists(), "icon.ico must exist")
        self.assertTrue(icon_icns.exists(), "icon.icns must exist")

        self.assertGreater(icon_ico.stat().st_size, 1000)
        self.assertGreater(icon_icns.stat().st_size, 1000)
        self.assertGreater(icon_png.stat().st_size, 1000)

        app_icon = gui_qt.get_application_icon()
        self.assertIsInstance(app_icon, QIcon)
        self.assertFalse(app_icon.isNull(), "Application icon must not be null")

    def test_custom_color_picker_support(self):
        """Verify PreferencesDialog has custom color picker button and handles custom hex."""
        pref_dlg = gui_qt.PreferencesDialog(None)
        try:
            self.assertTrue(hasattr(pref_dlg, "btn_custom_color"))
            self.assertTrue(hasattr(pref_dlg, "chk_prevent_sleep"))
            pref_dlg._on_theme_color_changed("#9333ea")
            self.assertEqual(pref_dlg.selected_theme, "#9333ea")
        finally:
            pref_dlg.close()

    def test_multi_audio_selection_in_gui(self):
        """Verify combo_audio_track contains Keep All Audio Tracks with index -1."""
        window = gui_qt.FocusApp()
        try:
            # Set audio tracks
            tracks = [
                (0, "Track 1: Japanese (Stereo)"),
                (1, "Track 2: English (5.1)")
            ]
            window._on_audio_tracks_loaded(tracks)
            
            # Check options
            count = window.combo_audio_track.count()
            self.assertGreaterEqual(count, 3) # Track 0, Track 1, and Keep All (-1)
            
            found_multi = False
            for i in range(count):
                if window.combo_audio_track.itemData(i) == -1:
                    found_multi = True
                    break
            self.assertTrue(found_multi, "Keep All Audio Tracks (-1) must be in audio track combo")
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
