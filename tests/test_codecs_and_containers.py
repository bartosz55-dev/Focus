import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import scenepack_generator_backend as backend
from scenepack_generator_gui_qt import FocusApp
from PySide6.QtWidgets import QApplication

# Ensure QApplication singleton for testing Qt widgets
app = QApplication.instance()
if app is None:
    app = QApplication([])


class TestCodecsAndContainers(unittest.TestCase):
    """Test suite verifying multi-codec (H.264, HEVC, AV1, ProRes) and container (MP4, MKV, MOV) support."""

    def setUp(self):
        self.generator = backend.ScenePackGenerator()

    def test_codec_probe_prores(self):
        """Test probing ProRes encoder."""
        codec, args = self.generator._get_best_video_codec_and_args(selected_codec="prores")
        self.assertTrue("prores" in codec.lower())

    def test_codec_probe_h264(self):
        """Test probing H.264 encoder."""
        codec, args = self.generator._get_best_video_codec_and_args(selected_codec="h264")
        self.assertTrue("264" in codec.lower() or "avc" in codec.lower())

    def test_codec_probe_hevc(self):
        """Test probing H.265 / HEVC encoder."""
        codec, args = self.generator._get_best_video_codec_and_args(selected_codec="hevc")
        self.assertTrue("hevc" in codec.lower() or "265" in codec.lower())

    def test_codec_probe_av1(self):
        """Test probing AV1 encoder."""
        codec, args = self.generator._get_best_video_codec_and_args(selected_codec="av1")
        self.assertTrue("av1" in codec.lower())

    def test_prores_pixel_format_and_mov_auto_switch(self):
        """Verify ProRes automatically requires .mov and sets yuv422p10le pixel format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            fake_video = tmp_path / "sample.mp4"
            fake_video.touch()
            output_mp4 = tmp_path / "result.mp4"

            # Mock ffmpeg / ffprobe execution
            with patch.object(self.generator, "run_subprocess") as mock_subproc, \
                 patch.object(self.generator, "_get_video_fps", return_value=24.0), \
                 patch.object(self.generator, "_get_video_duration", return_value=10.0), \
                 patch.object(self.generator, "_probe_color_metadata", return_value={"is_hdr": False, "vf_tonemap": []}):

                mock_subproc.return_value = MagicMock(returncode=0, stdout="", stderr="")

                # Run extract_and_concat with prores and mp4 output path
                self.generator.extract_and_concat(
                    fake_video,
                    [(0.0, 5.0, 0.5)],
                    output_mp4,
                    video_codec="prores",
                    container_format="auto"
                )

                # Find chunk command line calls
                chunk_calls = [
                    call[0][0] for call in mock_subproc.call_args_list
                    if isinstance(call[0][0], list) and "-pix_fmt" in call[0][0]
                ]
                self.assertTrue(len(chunk_calls) > 0, "No ffmpeg encode command found")
                chunk_cmd = chunk_calls[0]

                # Check pixel format is 10-bit 4:2:2
                pix_fmt_idx = chunk_cmd.index("-pix_fmt")
                self.assertEqual(chunk_cmd[pix_fmt_idx + 1], "yuv422p10le")

    def test_custom_container_mkv_and_mov(self):
        """Verify custom container formats produce proper file extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            fake_video = tmp_path / "sample.mp4"
            fake_video.touch()
            output_path = tmp_path / "result.mp4"

            with patch.object(self.generator, "run_subprocess") as mock_subproc, \
                 patch.object(self.generator, "_get_video_fps", return_value=24.0), \
                 patch.object(self.generator, "_get_video_duration", return_value=10.0), \
                 patch.object(self.generator, "_probe_color_metadata", return_value={"is_hdr": False, "vf_tonemap": []}):

                mock_subproc.return_value = MagicMock(returncode=0, stdout="", stderr="")

                # Request MKV container
                self.generator.extract_and_concat(
                    fake_video,
                    [(0.0, 5.0, 0.5)],
                    output_path,
                    video_codec="h264",
                    container_format="mkv"
                )

                # Check concat output file has .mkv extension
                concat_calls = [
                    call[0][0] for call in mock_subproc.call_args_list
                    if isinstance(call[0][0], list) and "-f" in call[0][0] and "concat" in call[0][0]
                ]
                self.assertTrue(len(concat_calls) > 0, "No concat command found")
                final_out = concat_calls[0][-1]
                self.assertTrue(str(final_out).endswith(".mkv"))


class TestQtGuiCodecsAndCheckpoints(unittest.TestCase):
    """Test suite verifying Qt GUI codec/container selectors and checkpoint loader."""

    def setUp(self):
        clean_settings = {
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
        with patch.object(FocusApp, "load_settings", return_value=clean_settings):
            self.gui = FocusApp()

    def tearDown(self):
        self.gui.close()

    def test_gui_codec_and_container_defaults(self):
        """Test that GUI elements for codec and container are initialized."""
        self.assertIsNotNone(self.gui.combo_video_codec)
        self.assertIsNotNone(self.gui.combo_container)
        self.assertIsNotNone(self.gui.btn_main_load_scan)
        self.assertIsNotNone(self.gui.btn_load_scan)

        self.assertEqual(self.gui._get_selected_video_codec_cli(), "auto")
        self.assertEqual(self.gui._get_selected_container_format_cli(), "mp4")

    def test_prores_auto_switches_container_in_gui(self):
        """Selecting Apple ProRes must switch container to MOV (.mov)."""
        # Ensure we start from Auto / MP4
        self.gui.combo_video_codec.setCurrentIndex(0)
        self.gui.combo_container.setCurrentIndex(0)
        self.gui.output_path_str = "/path/to/my_scenepack.mp4"

        prores_idx = -1
        for i in range(self.gui.combo_video_codec.count()):
            if "prores" in self.gui.combo_video_codec.itemText(i).lower():
                prores_idx = i
                break
        self.assertGreaterEqual(prores_idx, 0)
        self.gui.combo_video_codec.setCurrentIndex(prores_idx)

        # Container should now be MOV
        self.assertEqual(self.gui._get_selected_container_format_cli(), "mov")
        self.assertTrue(self.gui.output_path_str.endswith(".mov"))

    def test_load_scan_from_file_checkpoint_dict(self):
        """Test loading scan intervals from a dict checkpoint file."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({
                "intervals": [
                    {"source": "/path/video1.mp4", "start": 10.5, "end": 15.0, "avg_x": 0.45},
                    {"source": "/path/video1.mp4", "start": 20.0, "end": 28.5, "avg_x": 0.60}
                ]
            }, f)
            checkpoint_file = f.name

        try:
            with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName", return_value=(checkpoint_file, "JSON Files (*.json)")):
                self.gui.load_scan_from_file()

            self.assertEqual(len(self.gui.scanned_intervals), 2)
            self.assertEqual(self.gui.table_review.rowCount(), 2)
            self.assertEqual(self.gui.scanned_intervals[0][1], 10.5)
            self.assertEqual(self.gui.scanned_intervals[1][2], 28.5)
        finally:
            if os.path.exists(checkpoint_file):
                os.remove(checkpoint_file)


if __name__ == "__main__":
    unittest.main()
