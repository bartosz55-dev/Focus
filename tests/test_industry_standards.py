import unittest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import scenepack_generator_backend as backend


class TestIndustryStandardsAndQuality(unittest.TestCase):
    """Test suite verifying HDR tone-mapping, 320k audio, clips folder export, and smart naming."""

    def test_smart_scene_standard_filename(self):
        """Test formatting video filenames into the clean 411/scene standard format."""
        # 1. TV show with character, season, episode, resolution, source
        p1 = Path("Dexter.S01E04.1080p.BluRay.x264-DON.mkv")
        res1 = backend.generate_scene_standard_filename(p1, character_name="Dexter Morgan")
        self.assertIn("Dexter Morgan", res1)
        self.assertIn("Dexter", res1)
        self.assertIn("S01", res1)
        self.assertIn("1080p", res1)
        self.assertTrue(res1.endswith(".mp4"))

        # 2. Movie/Show with 4K UHD
        p2 = Path("The.Last.of.Us.2023.S01E01.2160p.UHD.HDR.mkv")
        res2 = backend.generate_scene_standard_filename(p2, character_name="Joel Miller")
        self.assertIn("Joel Miller", res2)
        self.assertIn("The Last of Us", res2)
        self.assertIn("S01", res2)
        self.assertTrue(res2.endswith(".mp4"))

        # 3. Anime format with episode and WEB-DL
        p3 = Path("[SubsPlease] Jujutsu Kaisen - 41 (1080p) [WEB-DL].mkv")
        res3 = backend.generate_scene_standard_filename(p3, character_name="Gojo Satoru")
        self.assertIn("Gojo Satoru", res3)
        self.assertIn("Jujutsu Kaisen", res3)
        self.assertTrue(res3.endswith(".mp4"))

        # 4. Fallback when no character is specified
        p4 = Path("Breaking.Bad.S05E14.1080p.BluRay.mkv")
        res4 = backend.generate_scene_standard_filename(p4, character_name=None)
        self.assertIn("Breaking Bad", res4)
        self.assertIn("S05", res4)
        self.assertTrue(res4.endswith(".mp4"))

    def test_probe_color_metadata_hdr_detection(self):
        """Verify _probe_color_metadata correctly identifies HDR10, HLG, and BT.2020 sources."""
        generator = backend.ScenePackGenerator()

        # Mock HDR10 (smpte2084 / BT.2020)
        hdr_mock_stdout = (
            '{\n'
            '  "streams": [\n'
            '    {\n'
            '      "color_space": "bt2020nc",\n'
            '      "color_transfer": "smpte2084",\n'
            '      "color_primaries": "bt2020",\n'
            '      "pix_fmt": "yuv420p10le"\n'
            '    }\n'
            '  ]\n'
            '}\n'
        )

        with patch.object(generator, "run_subprocess") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=hdr_mock_stdout, stderr="")
            meta = generator._probe_color_metadata(Path("movie_hdr.mkv"))
            self.assertTrue(meta.get("is_hdr"))
            self.assertEqual(meta.get("color_transfer"), "smpte2084")
            self.assertEqual(meta.get("color_space"), "bt2020nc")

        # Mock standard SDR (BT.709)
        sdr_mock_stdout = (
            '{\n'
            '  "streams": [\n'
            '    {\n'
            '      "color_space": "bt709",\n'
            '      "color_transfer": "bt709",\n'
            '      "color_primaries": "bt709",\n'
            '      "pix_fmt": "yuv420p"\n'
            '    }\n'
            '  ]\n'
            '}\n'
        )

        with patch.object(generator, "run_subprocess") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=sdr_mock_stdout, stderr="")
            meta = generator._probe_color_metadata(Path("show_sdr.mp4"))
            self.assertFalse(meta.get("is_hdr"))
            self.assertEqual(meta.get("color_transfer"), "bt709")

    def test_audio_bitrate_320k_configuration(self):
        """Verify default audio bitrate is studio-grade 320 kbps in backend configuration."""
        self.assertEqual(backend.STUDIO_AUDIO_BITRATE, "320k")

    def test_export_clips_folder_remux_calls(self):
        """Verify individual scene clips are remuxed when export_clips_folder is True."""
        generator = backend.ScenePackGenerator()
        intervals = [
            (Path("sample.mp4"), 10.0, 15.0, 0.5),
            (Path("sample.mp4"), 25.0, 30.0, 0.5)
        ]
        out_path = Path("/tmp/test_project/Master_Scenepack.mp4")

        def fake_run(cmd, *args, **kwargs):
            if isinstance(cmd, list) and len(cmd) > 0:
                last_arg = str(cmd[-1])
                if "chunk_" in last_arg:
                    p = Path(last_arg)
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(b"dummy_video_bytes")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch.object(generator, "run_subprocess", side_effect=fake_run) as mock_run, \
             patch.object(generator, "_get_video_fps", return_value=24.0), \
             patch.object(generator, "_probe_color_metadata", return_value={"is_hdr": False}), \
             patch("shutil.rmtree"), \
             patch.object(Path, "mkdir"):

            # Call extract_and_concat with export_clips_folder=True
            generator.extract_and_concat(
                video_path=Path("sample.mp4"),
                intervals=intervals,
                output_path=out_path,
                export_clips_folder=True
            )

            # Check that remux_cmd was called for each chunk with faststart
            all_cmds = [call.args[0] for call in mock_run.call_args_list if call.args and isinstance(call.args[0], list)]
            remux_calls = [cmd for cmd in all_cmds if "+faststart" in cmd and "copy" in cmd and "Scene_" in str(cmd[-1])]
            self.assertEqual(len(remux_calls), 2)
            self.assertIn("Scene_001.mp4", str(remux_calls[0][-1]))
            self.assertIn("Scene_002.mp4", str(remux_calls[1][-1]))

    def test_cli_export_clips_folder_argument(self):
        """Verify CLI argument parser correctly parses --export-clips-folder."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--export-clips-folder", action="store_true")
        parser.add_argument("--no-crop-black-bars", action="store_true")
        parser.add_argument("--export-xml", action="store_true", default=True)
        parser.add_argument("--no-export-xml", dest="export_xml", action="store_false")

        args1 = parser.parse_args(["--export-clips-folder"])
        self.assertTrue(args1.export_clips_folder)
        self.assertFalse(args1.no_crop_black_bars)
        self.assertTrue(args1.export_xml)

        args2 = parser.parse_args(["--no-crop-black-bars", "--no-export-xml"])
        self.assertTrue(args2.no_crop_black_bars)
        self.assertFalse(args2.export_xml)

    def test_detect_letterbox_crop_with_black_bars(self):
        """Verify _detect_letterbox_crop accurately detects letterboxing and returns crop filter."""
        import numpy as np
        import cv2
        generator = backend.ScenePackGenerator()

        mock_frame = np.ones((1080, 1920, 3), dtype=np.uint8) * 128
        mock_frame[0:140, :, :] = 0
        mock_frame[1080-140:, :, :] = 0

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: 1000 if prop == cv2.CAP_PROP_FRAME_COUNT else (1920 if prop == cv2.CAP_PROP_FRAME_WIDTH else (1080 if prop == cv2.CAP_PROP_FRAME_HEIGHT else 24.0))
        mock_cap.read.return_value = (True, mock_frame)

        with patch("cv2.VideoCapture", return_value=mock_cap), \
             patch.object(Path, "exists", return_value=True):
            crop_res = generator._detect_letterbox_crop(Path("letterbox_movie.mkv"))
            self.assertEqual(crop_res, "crop=1920:800:0:140")

    def test_detect_letterbox_crop_full_frame(self):
        """Verify _detect_letterbox_crop returns empty string when no black bars are present."""
        import numpy as np
        import cv2
        generator = backend.ScenePackGenerator()

        mock_frame = np.ones((1080, 1920, 3), dtype=np.uint8) * 128

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: 1000 if prop == cv2.CAP_PROP_FRAME_COUNT else (1920 if prop == cv2.CAP_PROP_FRAME_WIDTH else (1080 if prop == cv2.CAP_PROP_FRAME_HEIGHT else 24.0))
        mock_cap.read.return_value = (True, mock_frame)

        with patch("cv2.VideoCapture", return_value=mock_cap), \
             patch.object(Path, "exists", return_value=True):
            crop_res = generator._detect_letterbox_crop(Path("full_frame_show.mp4"))
            self.assertEqual(crop_res, "")

    def test_generate_premiere_xml(self):
        """Verify generate_premiere_xml produces valid FCPXML xmeml v4 timeline."""
        import xml.etree.ElementTree as ET
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            xml_out = Path(tmpdir) / "test_timeline.xml"
            dummy_video = Path(tmpdir) / "my_video.mp4"
            dummy_video.write_bytes(b"dummy")
            intervals = [(5.0, 10.0), (20.0, 35.0)]

            res_path = backend.generate_premiere_xml(
                video_path=dummy_video,
                intervals=intervals,
                output_xml_path=xml_out,
                fps=24.0,
                sequence_name="Test Sequence"
            )
            self.assertTrue(xml_out.exists())
            tree = ET.parse(xml_out)
            root = tree.getroot()
            self.assertEqual(root.tag, "xmeml")
            self.assertEqual(root.attrib.get("version"), "4")
            seq = root.find("sequence")
            self.assertIsNotNone(seq)
            self.assertEqual(seq.find("name").text, "Test Sequence")
            self.assertEqual(seq.find("duration").text, "480")
            v_track = seq.find("media/video/track")
            self.assertIsNotNone(v_track)
            clipitems = v_track.findall("clipitem")
            self.assertEqual(len(clipitems), 2)
            self.assertEqual(clipitems[0].find("in").text, "120")
            self.assertEqual(clipitems[0].find("out").text, "240")

    def test_generate_scenepack_spec_report(self):
        """Verify generate_scenepack_spec_report creates comprehensive info file."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            info_out = Path(tmpdir) / "test_info.txt"
            dummy_video = Path(tmpdir) / "sample_show.mp4"
            intervals = [(10.0, 25.5), (40.0, 52.0)]

            res = backend.generate_scenepack_spec_report(
                output_path=info_out,
                video_path=dummy_video,
                intervals=intervals,
                fps=24.0,
                character_name="Eren Yeager",
                crop_info="crop=1920:800:0:140"
            )
            self.assertTrue(info_out.exists())
            content = info_out.read_text(encoding="utf-8")
            self.assertIn("FOCUS SCENEPACK MASTER SPECIFICATION", content)
            self.assertIn("Eren Yeager", content)
            self.assertIn("sample_show.mp4", content)
            self.assertIn("24.000 fps", content)
            self.assertIn("320k", content)
            self.assertIn("crop=1920:800:0:140", content)
            self.assertIn("Adobe After Effects", content)
            self.assertIn("CapCut", content)


if __name__ == "__main__":
    unittest.main()
