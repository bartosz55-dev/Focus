import unittest
import os
import tempfile
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch

import scenepack_generator_backend as backend
from scenepack_generator_backend import ScenePackGenerator


class TestVadAndAnimePipeline(unittest.TestCase):
    def setUp(self):
        self.generator = ScenePackGenerator(mode="Anime")

    def test_anime_cascade_path_bundled_or_local_discovery(self):
        """Verify anime cascade locates models/ directory when available."""
        self.assertTrue(self.generator.anime_cascade_path.exists())
        self.assertGreater(self.generator.anime_cascade_path.stat().st_size, 50000)

    def test_detect_silences_parses_ffmpeg_info_output(self):
        """Verify _detect_silences correctly parses silence_start and silence_end from FFmpeg output."""
        fake_stderr = (
            "[Parsed_silencedetect_0 @ 0x123] silence_start: 12.345\n"
            "[Parsed_silencedetect_0 @ 0x123] silence_end: 15.678 | silence_duration: 3.333\n"
            "[Parsed_silencedetect_0 @ 0x123] silence_start: 22.0\n"
            "[Parsed_silencedetect_0 @ 0x123] silence_end: 25.5 | silence_duration: 3.5\n"
        )
        with patch.object(self.generator, "run_subprocess") as mock_subproc:
            mock_subproc.return_value = MagicMock(stderr=fake_stderr)
            silences = self.generator._detect_silences(Path("fake_video.mp4"), buffer_ms=300)
            self.assertEqual(len(silences), 2)
            self.assertEqual(silences[0], (12.345, 15.678))
            self.assertEqual(silences[1], (22.0, 25.5))

    def test_build_target_voice_print_safely_unpacks_2tuple_and_3tuple(self):
        """Verify _build_target_voice_print handles 2-tuples and 3-tuples without ValueError."""
        test_intervals_2tuple = [(10.0, 15.0), (20.0, 25.0)]
        test_intervals_3tuple = [(10.0, 15.0, 0.6), (20.0, 25.0, 0.4)]

        fake_embedding = np.ones(13, dtype=np.float32)
        with patch.object(self.generator, "_extract_audio_embedding", return_value=fake_embedding):
            vp2 = self.generator._build_target_voice_print(Path("fake.mp4"), test_intervals_2tuple)
            self.assertIsNotNone(vp2)
            self.assertEqual(vp2.shape, (13,))

            vp3 = self.generator._build_target_voice_print(Path("fake.mp4"), test_intervals_3tuple)
            self.assertIsNotNone(vp3)
            self.assertEqual(vp3.shape, (13,))

    def test_scan_and_prepare_fails_fast_on_empty_intervals(self):
        """Verify scan_and_prepare does not run expensive scene cut / silence detection if find_scenes returns empty."""
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tf_v, tempfile.NamedTemporaryFile(suffix=".jpg") as tf_i:
            with patch.object(self.generator, "find_scenes", return_value=[]), \
                 patch.object(self.generator, "load_reference_face", return_value=(np.zeros((16, 16)), np.zeros((16, 16)), np.zeros(256))), \
                 patch.object(self.generator, "_detect_scene_cuts") as mock_cuts, \
                 patch.object(self.generator, "_detect_silences") as mock_silences, \
                 patch.object(self.generator, "_check_and_download_ffmpeg"):

                with self.assertRaises(ValueError) as ctx:
                    self.generator.scan_and_prepare(
                        video_path=tf_v.name,
                        ref_image_path=tf_i.name,
                        vad_enabled=True
                    )
                self.assertIn("Target face was not detected", str(ctx.exception))
                mock_cuts.assert_not_called()
                mock_silences.assert_not_called()

    def test_voice_verification_fallback_protects_detected_scenes(self):
        """Verify that if voice verification threshold rejects all clips, detected visual intervals are preserved."""
        fake_intervals = [(10.0, 15.0, 0.5), (30.0, 35.0, 0.5)]

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tf_v, tempfile.NamedTemporaryFile(suffix=".jpg") as tf_i:
            with patch.object(self.generator, "find_scenes", return_value=fake_intervals), \
                 patch.object(self.generator, "load_reference_face", return_value=(np.zeros((16, 16)), np.zeros((16, 16)), np.zeros(256))), \
                 patch.object(self.generator, "_detect_scene_cuts", return_value=[]), \
                 patch.object(self.generator, "_detect_silences", return_value=[(1.0, 5.0)]), \
                 patch.object(self.generator, "_build_target_voice_print", return_value=np.ones(13)), \
                 patch.object(self.generator, "_extract_audio_embedding", return_value=np.zeros(13)), \
                 patch.object(self.generator, "_check_and_download_ffmpeg"):

                result = self.generator.scan_and_prepare(
                    video_path=tf_v.name,
                    ref_image_path=tf_i.name,
                    vad_enabled=True,
                    vad_speaker_enabled=True,
                    vad_speaker_threshold=0.99
                )
                self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
