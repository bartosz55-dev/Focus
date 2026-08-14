import unittest
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scenepack_generator_gui import ScenePackGenerator, get_translation, TRANSLATIONS


class MockQueue:
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)

    def empty(self):
        return len(self.items) == 0

    def get(self):
        return self.items.pop(0)


class TestScenePackGeneratorLogic(unittest.TestCase):

    def setUp(self):
        self.queue = MockQueue()
        self.generator = ScenePackGenerator(log_queue=self.queue, frame_skip=15)

    def test_merge_intervals_empty(self):
        result = self.generator.merge_intervals([], padding_before=2.0, padding_after=2.0, duration=100.0)
        self.assertEqual(result, [])

    def test_merge_intervals_single(self):
        # Face detected at t=10.0s, padding=2.0s -> clip from 8.0s to 12.0s
        result = self.generator.merge_intervals([10.0], padding_before=2.0, padding_after=2.0, duration=100.0)
        self.assertEqual(result, [(8.0, 12.0)])

    def test_merge_intervals_gap_bridging(self):
        # Detections at 10.0, 11.0, 12.0 (gap <= 1.5s max_gap) -> continuous scene from 10.0 to 12.0
        # Padded with before=2.0, after=2.0 -> clip from 8.0 to 14.0
        result = self.generator.merge_intervals([10.0, 11.0, 12.0], padding_before=2.0, padding_after=2.0, duration=100.0, max_gap_tolerance=1.5)
        self.assertEqual(result, [(8.0, 14.0)])

    def test_merge_intervals_separate_scenes(self):
        # Detections at 10.0s and 30.0s (gap 20s > 1.5s) -> separate scenes
        # Scene 1: 8.0 to 12.0, Scene 2: 28.0 to 32.0
        result = self.generator.merge_intervals([10.0, 30.0], padding_before=2.0, padding_after=2.0, duration=100.0, max_gap_tolerance=1.5)
        self.assertEqual(result, [(8.0, 12.0), (28.0, 32.0)])

    def test_merge_intervals_boundary_clamping(self):
        # Detection at t=1.0s, padding_before=3.0s -> clamped to 0.0
        # Detection at t=99.0s, duration=100.0s, padding_after=3.0s -> clamped to 100.0
        result1 = self.generator.merge_intervals([1.0], padding_before=3.0, padding_after=1.0, duration=100.0)
        self.assertEqual(result1, [(0.0, 2.0)])

        result2 = self.generator.merge_intervals([99.0], padding_before=1.0, padding_after=3.0, duration=100.0)
        self.assertEqual(result2, [(98.0, 100.0)])

    def test_merge_intervals_negative_timestamps_ignored(self):
        # Negative timestamps should be filtered out
        result = self.generator.merge_intervals([-5.0, -1.0, 10.0], padding_before=2.0, padding_after=2.0, duration=100.0)
        self.assertEqual(result, [(8.0, 12.0)])

    def test_min_scene_duration_expansion(self):
        # Detection at t=10.0s with padding_before=0.1, padding_after=0.1 -> initial clip (9.9, 10.1) duration 0.2s
        # min_scene_duration=1.0s -> expanded to (9.9, 10.9)
        result = self.generator.merge_intervals([10.0], padding_before=0.1, padding_after=0.1, duration=100.0, min_scene_duration=1.0)
        self.assertEqual(result, [(9.9, 10.9)])

    def test_merge_intervals_tuple_input(self):
        # When input is list of tuples (timestamp, rel_x), result must contain (start, end, avg_x)
        result = self.generator.merge_intervals([(10.0, 0.2), (11.0, 0.4)], padding_before=2.0, padding_after=2.0, duration=100.0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], 8.0)
        self.assertEqual(result[0][1], 13.0)
        self.assertAlmostEqual(result[0][2], 0.3)

    def test_dlib_thread_lock_exists(self):
        import scenepack_generator_backend as backend
        import threading
        self.assertTrue(hasattr(backend, 'DLIB_THREAD_LOCK'))
        self.assertIsInstance(backend.DLIB_THREAD_LOCK, type(threading.Lock()))

    def test_parse_video_paths(self):
        from scenepack_generator_backend import parse_video_paths
        from pathlib import Path
        
        # Single string
        res = parse_video_paths("/path/to/vid1.mp4")
        self.assertEqual(res, [Path("/path/to/vid1.mp4").resolve()])
        
        # List of strings
        res = parse_video_paths(["/path/to/v1.mp4", "/path/to/v2.mp4"])
        self.assertEqual(len(res), 2)
        
        # Semicolon separated string
        res = parse_video_paths("/path/to/v1.mp4;/path/to/v2.mp4")
        self.assertEqual(len(res), 2)

    def test_check_lip_movement_defined(self):
        self.assertTrue(hasattr(self.generator, '_check_lip_movement'))
        import inspect
        sig = inspect.signature(self.generator._check_lip_movement)
        self.assertIn('video_path', sig.parameters)
        self.assertIn('target_encoding', sig.parameters)

    def test_get_audio_tracks_multivideo_support(self):
        tracks = self.generator.get_audio_tracks("/path/nonexistent1.mp4;/path/nonexistent2.mp4")
        self.assertIsInstance(tracks, list)
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0][0], 0)

    def test_find_scenes_multivideo_signature(self):
        import inspect
        sig = inspect.signature(self.generator.find_scenes)
        self.assertIn('video_index', sig.parameters)
        self.assertIn('total_videos', sig.parameters)
        self.assertEqual(sig.parameters['video_index'].default, 0)
        self.assertEqual(sig.parameters['total_videos'].default, 1)

    def test_anime_feature_extraction_and_matching(self):
        from scenepack_generator_backend import extract_anime_face_features, is_anime_feature_match
        import numpy as np
        # Create identical mock crops
        crop1 = np.full((64, 64, 3), (120, 180, 240), dtype=np.uint8)
        crop2 = np.full((64, 64, 3), (120, 180, 240), dtype=np.uint8)
        # Create different color mock crop
        crop3 = np.full((64, 64, 3), (255, 30, 30), dtype=np.uint8)

        feat1 = extract_anime_face_features(crop1)
        feat2 = extract_anime_face_features(crop2)
        feat3 = extract_anime_face_features(crop3)

        self.assertTrue(is_anime_feature_match(feat1, feat2))
        self.assertFalse(is_anime_feature_match(feat1, feat3))

        # Test extractor helper
        feats_list = self.generator._extract_anime_features_list({'anime_feature': feat1})
        self.assertEqual(len(feats_list), 1)
        self.assertTrue(is_anime_feature_match(feats_list[0], feat2))


class TestTranslationFallback(unittest.TestCase):

    def test_translation_existing_key(self):
        self.assertEqual(get_translation("English", "dashboard"), "Dashboard")
        self.assertEqual(get_translation("Polski", "dashboard"), "Panel Główny")

    def test_translation_missing_key_in_lang_fallback_to_english(self):
        # Mocking a missing key in a language dictionary
        result = get_translation("NonExistentLang", "dashboard")
        self.assertEqual(result, "Dashboard")

    def test_translation_completely_missing_key(self):
        result = get_translation("Polski", "completely_unknown_xyz_key")
        self.assertEqual(result, "completely_unknown_xyz_key")


if __name__ == "__main__":
    unittest.main()
