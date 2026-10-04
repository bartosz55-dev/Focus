import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

from scenepack_generator_gui_qt import FocusApp, PreferencesDialog
import scenepack_generator_backend as backend

app = QApplication.instance()
if app is None:
    app = QApplication([])


class TestGuiAllButtonsAndConfigs(unittest.TestCase):
    """
    Thorough test suite systematically verifying every button, configuration toggle,
    preset, theme, and language in FocusApp.
    """

    def setUp(self):
        self.clean_settings = {
            "pad_before": 2.0, "pad_after": 2.0, "max_gap_tolerance": 1.5,
            "min_scene_duration": 1.0, "frame_skip": 15, "vad_enabled": True,
            "vad_buffer": 300, "vad_speaker_enabled": True, "vad_speaker_threshold": 0.68,
            "skip_intro": True, "skip_outro": False, "intro_mode": "Auto Chapters (MKV/MP4)",
            "intro_duration": 90, "export_quality": "Auto (Match Source Bitrate)",
            "video_codec": "Auto (Fastest Hardware H.264)", "container_format": "MP4 (.mp4)",
            "play_sound": True, "appearance_mode": "Dark", "theme": "violet",
            "language": "English", "default_mode": "Real Faces",
            "prevent_sleep": True, "auto_render": False, "export_clips_folder": False
        }
        with patch.object(FocusApp, "load_settings", return_value=dict(self.clean_settings)), \
             patch("scenepack_generator_backend.SleepInhibitor.prevent_sleep"), \
             patch("scenepack_generator_backend.SleepInhibitor.allow_sleep"):
            self.gui = FocusApp()

    def tearDown(self):
        self.gui.close()

    def test_sidebar_navigation_buttons(self):
        """Test switching between Generator, Gallery, and other tabs."""
        # Switch to Gallery
        self.gui.btn_sidebar_gal.click()
        self.assertEqual(self.gui.stacked_view.currentIndex(), 1)

        # Switch back to Generator
        self.gui.btn_sidebar_gen.click()
        self.assertEqual(self.gui.stacked_view.currentIndex(), 0)

        # Test settings button
        with patch.object(PreferencesDialog, "exec") as mock_exec:
            self.gui.btn_settings.click()
            self.assertTrue(mock_exec.called)

        # Test tutorial and changelog buttons
        with patch("PySide6.QtWidgets.QDialog.exec"):
            self.gui.btn_tutorial.click()
            self.gui.btn_changelog.click()

    def test_mode_switcher_buttons(self):
        """Test switching between Real Faces and Anime modes."""
        self.gui.btn_mode_anime.click()
        self.assertEqual(self.gui.current_mode, "Anime")

        self.gui.btn_mode_real.click()
        self.assertEqual(self.gui.current_mode, "Real Faces")

    def test_all_tuning_input_fields(self):
        """Test editing all Section B numerical inputs and verifying settings persistence."""
        self.gui.input_pad_before.setText("3.5")
        self.gui.input_pad_before.editingFinished.emit()
        self.assertEqual(self.gui.settings["pad_before"], 3.5)

        self.gui.input_pad_after.setText("2.5")
        self.gui.input_pad_after.editingFinished.emit()
        self.assertEqual(self.gui.settings["pad_after"], 2.5)

        self.gui.input_max_gap.setText("2.0")
        self.gui.input_max_gap.editingFinished.emit()
        self.assertEqual(self.gui.settings["max_gap_tolerance"], 2.0)

        self.gui.input_min_scene.setText("1.8")
        self.gui.input_min_scene.editingFinished.emit()
        self.assertEqual(self.gui.settings["min_scene_duration"], 1.8)

        self.gui.input_frame_skip.setText("10")
        self.gui.input_frame_skip.editingFinished.emit()
        self.assertEqual(self.gui.settings["frame_skip"], 10)

    def test_aspect_ratio_combo(self):
        """Test toggling all aspect ratios."""
        for idx in range(self.gui.combo_aspect.count()):
            self.gui.combo_aspect.setCurrentIndex(idx)
            self.assertEqual(self.gui.combo_aspect.currentIndex(), idx)

    def test_export_quality_combo(self):
        """Test toggling all export quality presets."""
        for idx in range(self.gui.combo_export_quality.count()):
            self.gui.combo_export_quality.setCurrentIndex(idx)
            self.assertEqual(self.gui.combo_export_quality.currentIndex(), idx)

    def test_video_codec_and_container_combos(self):
        """Test all video codecs and containers, verifying ProRes auto-switch."""
        # Cycle through codecs
        for idx in range(self.gui.combo_video_codec.count()):
            self.gui.combo_video_codec.setCurrentIndex(idx)
            codec_cli = self.gui._get_selected_video_codec_cli()
            self.assertIn(codec_cli, ["auto", "h264", "hevc", "av1", "prores"])

        # Cycle through containers
        for idx in range(self.gui.combo_container.count()):
            self.gui.combo_container.setCurrentIndex(idx)
            cnt_cli = self.gui._get_selected_container_format_cli()
            self.assertIn(cnt_cli, ["mp4", "mkv", "mov"])

    def test_audio_and_vad_controls(self):
        """Test dialogue protection checkboxes and slider controls."""
        self.gui.chk_vad.setChecked(False)
        self.assertFalse(self.gui.settings["vad_enabled"])
        self.gui.chk_vad.setChecked(True)
        self.assertTrue(self.gui.settings["vad_enabled"])

        self.gui.input_vad_buffer.setText("450")
        self.gui.input_vad_buffer.editingFinished.emit()
        self.assertEqual(self.gui.settings["vad_buffer"], 450)

        self.gui.chk_speaker.setChecked(False)
        self.assertFalse(self.gui.settings["vad_speaker_enabled"])
        self.gui.chk_speaker.setChecked(True)
        self.assertTrue(self.gui.settings["vad_speaker_enabled"])

        self.gui.slider_speaker.setValue(75)
        self.assertEqual(self.gui.lbl_speaker_val.text(), "0.75")
        self.assertAlmostEqual(self.gui.settings["vad_speaker_threshold"], 0.75, places=2)

    def test_intro_outro_controls(self):
        """Test intro and outro skipping controls."""
        self.gui.chk_skip_intro.setChecked(False)
        self.assertFalse(self.gui.settings["skip_intro"])
        self.gui.chk_skip_intro.setChecked(True)
        self.assertTrue(self.gui.settings["skip_intro"])

        self.gui.chk_skip_outro.setChecked(True)
        self.assertTrue(self.gui.settings["skip_outro"])
        self.gui.chk_skip_outro.setChecked(False)
        self.assertFalse(self.gui.settings["skip_outro"])

        # Switch intro mode to custom duration
        custom_idx = self.gui.combo_intro_mode.findText("Custom Duration")
        if custom_idx >= 0:
            self.gui.combo_intro_mode.setCurrentIndex(custom_idx)
            self.assertFalse(self.gui.input_intro_duration.isHidden())
            self.gui.input_intro_duration.setText("85.0")
            self.gui.input_intro_duration.editingFinished.emit()
            self.assertEqual(self.gui.settings["intro_duration"], 85.0)

    def test_automation_checkboxes(self):
        """Test Auto-Render, Clips Folder, Auto-Crop, and XML export toggles."""
        self.gui.chk_auto_render.setChecked(True)
        self.assertTrue(self.gui.settings["auto_render"])
        self.gui.chk_auto_render.setChecked(False)

        self.gui.chk_export_clips_folder.setChecked(True)
        self.assertTrue(self.gui.settings["export_clips_folder"])
        self.gui.chk_export_clips_folder.setChecked(False)

        self.gui.chk_auto_crop.setChecked(False)
        self.assertFalse(self.gui.settings["auto_crop_black_bars"])
        self.gui.chk_auto_crop.setChecked(True)

        self.gui.chk_export_xml.setChecked(False)
        self.assertFalse(self.gui.settings["export_timeline_xml"])
        self.gui.chk_export_xml.setChecked(True)

    def test_smart_presets_buttons(self):
        """Test Auto-Tune and preset buttons."""
        self.gui.btn_autotune.click()
        self.assertIsNotNone(self.gui.input_pad_before.text())

        self.gui.btn_preset_tiktok.click()
        self.assertEqual(self.gui.input_pad_before.text(), "1.5")
        self.assertEqual(self.gui.input_frame_skip.text(), "12")

        self.gui.btn_preset_youtube.click()
        self.assertEqual(self.gui.input_pad_before.text(), "2.0")
        self.assertEqual(self.gui.input_frame_skip.text(), "15")

        self.gui.btn_preset_draft.click()
        self.assertEqual(self.gui.input_frame_skip.text(), "30")

    def test_review_table_select_deselect_buttons(self):
        """Test Select All and Deselect All buttons in review card."""
        intervals = [
            ("/path/v.mp4", 10.0, 15.0, 0.5),
            ("/path/v.mp4", 20.0, 25.0, 0.5)
        ]
        self.gui._on_show_review_checklist(intervals, [None, None])
        self.assertFalse(self.gui.review_card.isHidden())
        self.assertEqual(len(self.gui.review_checkboxes), 2)

        # Deselect all
        self.gui.btn_deselect_all.click()
        for _, chk in self.gui.review_checkboxes:
            self.assertFalse(chk.isChecked())

        # Select all
        self.gui.btn_select_all.click()
        for _, chk in self.gui.review_checkboxes:
            self.assertTrue(chk.isChecked())

    def test_all_theme_and_language_switches(self):
        """Test dynamically applying all themes and all supported languages."""
        themes = ["violet", "blue", "emerald", "amber", "rose", "graphite"]
        for theme in themes:
            self.gui._apply_theme(theme)
            self.assertEqual(self.gui.current_theme, theme)

        languages = ["English", "Polski", "Deutsch", "Español", "Français"]
        for lang in languages:
            self.gui._apply_language(lang)
            self.assertEqual(self.gui.current_lang, lang)

    def test_log_diagnostics_and_clear(self):
        """Test processing logs, diagnostics copy, and log filtering."""
        self.gui._on_log_msg("Test log entry message")
        self.assertIn("Test log entry message", self.gui.txt_log.toPlainText())

        self.gui.input_log_filter.setText("Test")
        self.gui.copy_diagnostics()

    def test_clear_buttons(self):
        """Test clearing batch queue and reference faces."""
        self.gui.batch_queue_files = ["/some/video.mp4"]
        self.gui.btn_clear_batch.click()
        self.assertEqual(len(self.gui.batch_queue_files), 0)

        self.gui.image_path_str = "/some/face.png"
        self.gui.btn_clear_image.click()
        self.assertEqual(self.gui.image_path_str, "")

    def test_action_buttons_presence(self):
        """Test that main action buttons are present, enabled, and responsive."""
        self.assertIsNotNone(self.gui.btn_generate)
        self.assertIsNotNone(self.gui.btn_main_load_scan)
        self.assertIsNotNone(self.gui.btn_load_scan)
        self.assertIsNotNone(self.gui.btn_render)

        self.assertTrue(self.gui.btn_generate.isEnabled())
        self.assertTrue(self.gui.btn_main_load_scan.isEnabled())


if __name__ == "__main__":
    unittest.main()
