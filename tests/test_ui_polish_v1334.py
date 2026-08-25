import unittest
import os
import sys
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication(sys.argv)

import scenepack_generator_backend as backend
import scenepack_generator_gui_qt as gui_qt


class TestUIPolishV1334(unittest.TestCase):
    """Test suite verifying all v1.3.34 UI polish items and bug fixes."""

    def test_translations_no_raw_leaks(self):
        """Ensure all languages provide clean translations for section headers and CTAs."""
        for lang in ["English", "Polski", "Deutsch", "Español", "Français", "日本語"]:
            wf = backend.get_translation(lang, "sec_workflow")
            res = backend.get_translation(lang, "sec_resources")
            sel_out = backend.get_translation(lang, "sel_output")
            vad = backend.get_translation(lang, "vad_enable")
            gen = backend.get_translation(lang, "generate")

            self.assertFalse(wf.startswith("sec_"), f"Raw leak in {lang}: {wf}")
            self.assertFalse(res.startswith("sec_"), f"Raw leak in {lang}: {res}")
            self.assertFalse(" _" in sel_out or "_Output" in sel_out, f"Underscore glitch in {lang}: {sel_out}")
            self.assertFalse(" _" in vad or "_Lip" in vad, f"Underscore glitch in {lang}: {vad}")
            self.assertFalse(" _" in gen or "_Analyze" in gen, f"Underscore glitch in {lang}: {gen}")

    def test_clean_fallback_for_unknown_keys(self):
        """Ensure fallback never leaks raw 'sec_' prefixes into the UI."""
        self.assertEqual(backend.get_translation("UnknownLang", "sec_workflow"), "WORKFLOW")
        self.assertEqual(backend.get_translation("UnknownLang", "sec_new_section"), "NEW SECTION")

    def test_gui_window_structure(self):
        """Verify window elements, sidebar width, single source of navigation truth, and grid alignment."""
        window = gui_qt.FocusApp()
        try:
            # 1. Sidebar width
            self.assertGreaterEqual(window.sidebar.width(), 240)
            self.assertGreaterEqual(window.sidebar.minimumWidth(), 240)

            # 2. Section Headers
            self.assertIn(window.lbl_wf.text(), ["WORKFLOW", "PROJEKT / WORKFLOW", "FLUJO DE TRABAJO", "ワークフロー", "RESSOURCEN"])
            self.assertIn(window.lbl_res.text(), ["RESOURCES", "MATERIAŁY", "RESSOURCEN", "RECURSOS", "リソース"])

            # 3. No redundant tab_box in header
            self.assertFalse(hasattr(window, "btn_tab_gen"))
            self.assertFalse(hasattr(window, "btn_tab_gal"))

            # 4. Path display heights
            self.assertGreaterEqual(window.lbl_video_path.minimumHeight(), 36)
            self.assertGreaterEqual(window.lbl_image_path.minimumHeight(), 36)
            self.assertGreaterEqual(window.lbl_output_path.minimumHeight(), 36)

            # 5. Dialogue & Speaker controls
            self.assertTrue(hasattr(window, "chk_vad"))
            self.assertTrue(hasattr(window, "input_vad_buffer"))
            self.assertTrue(hasattr(window, "chk_speaker"))
            self.assertTrue(hasattr(window, "slider_speaker"))
            self.assertTrue(hasattr(window, "lbl_speaker_val"))

            # 6. Intro & Outro controls
            self.assertTrue(hasattr(window, "chk_skip_intro"))
            self.assertTrue(hasattr(window, "chk_skip_outro"))
            self.assertTrue(hasattr(window, "combo_intro_mode"))
            self.assertTrue(hasattr(window, "input_intro_duration"))

            # 7. Navigation switching
            window._switch_main_view(1)
            self.assertEqual(window.stacked_view.currentIndex(), 1)
            self.assertTrue(window.btn_sidebar_gal.isChecked())
            self.assertFalse(window.btn_sidebar_gen.isChecked())

            window._switch_main_view(0)
            self.assertEqual(window.stacked_view.currentIndex(), 0)
            self.assertTrue(window.btn_sidebar_gen.isChecked())
            self.assertFalse(window.btn_sidebar_gal.isChecked())
        finally:
            window.close()

    def test_default_appearance_and_language(self):
        """Verify default language detection and System appearance mode."""
        detected_lang = gui_qt.detect_default_system_language()
        self.assertIn(detected_lang, ["English", "Polski", "Deutsch", "Español", "Français", "Русский", "Українська", "日本語"])

        # Check raw unconfigured default settings dictionary initialization
        from unittest.mock import patch
        with patch("pathlib.Path.exists", return_value=False):
            defaults = gui_qt.FocusApp.load_settings(gui_qt.FocusApp.__new__(gui_qt.FocusApp))
            self.assertEqual(defaults.get("appearance_mode"), "System")
            self.assertEqual(defaults.get("language"), detected_lang)


if __name__ == "__main__":
    unittest.main()

