import unittest
import sys
import os
import platform
import subprocess
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import scenepack_generator
import scenepack_generator_gui


class TestCrossPlatformCreationFlags(unittest.TestCase):
    """Verifies Windows CREATE_NO_WINDOW flag setup across backend modules."""
    
    def test_creation_flags_constant_defined(self):
        expected_flag = getattr(subprocess, "CREATE_NO_WINDOW", 0) if platform.system() == "Windows" else 0
        self.assertTrue(hasattr(scenepack_generator, "CREATE_NO_WINDOW"), "scenepack_generator must define CREATE_NO_WINDOW")
        self.assertTrue(hasattr(scenepack_generator_gui, "CREATE_NO_WINDOW"), "scenepack_generator_gui must define CREATE_NO_WINDOW")
        self.assertEqual(scenepack_generator.CREATE_NO_WINDOW, expected_flag)
        self.assertEqual(scenepack_generator_gui.CREATE_NO_WINDOW, expected_flag)


class TestConcatListFormatting(unittest.TestCase):
    """Verifies UTF-8 encoding and slash normalization in FFmpeg concat list generation."""
    
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_concat_"))
        
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def test_write_concat_list_utf8_and_slashes(self):
        # Simulate chunk files with Polish diacritics, spaces, and quotes
        chunk_names = [
            "scena_001_zażółć_gęślą_jaźń.mp4",
            "cięcie_002_łąka 'wiosenna'.mp4",
            "test\\windows\\backslash_path.mp4" # backslash simulation
        ]
        chunk_paths = [self.test_dir / name for name in chunk_names]
        concat_list_path = self.test_dir / "concat_list.txt"
        
        # Test helper function in scenepack_generator_gui
        self.assertTrue(hasattr(scenepack_generator_gui, "write_concat_list"), "scenepack_generator_gui must define write_concat_list")
        scenepack_generator_gui.write_concat_list(chunk_paths, concat_list_path)
        
        self.assertTrue(concat_list_path.exists())
        
        # Read back explicitly as UTF-8
        with open(concat_list_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]
            
        self.assertEqual(len(lines), 3)
        self.assertIn("zażółć_gęślą_jaźń", lines[0])
        self.assertNotIn("\\", lines[0])
        self.assertNotIn("\\", lines[2]) # Backslashes should be normalized to forward slashes /
        self.assertIn("'\\''", lines[1]) # Quotes should be escaped for FFmpeg concat demuxer


class TestVideoCaptureHygiene(unittest.TestCase):
    """Verifies that cv2.VideoCapture handles are properly released even when exceptions occur."""
    
    @patch("cv2.VideoCapture")
    def test_duration_check_releases_handle_on_exception(self, mock_cap_cls):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = Exception("Simulated OpenCV get error")
        mock_cap_cls.return_value = mock_cap
        
        generator = scenepack_generator.ScenePackGenerator(frame_skip=15)
        
        # Calling _get_video_duration should catch or raise, but MUST call release()
        try:
            generator._get_video_duration(Path("dummy_path.mp4"))
        except Exception:
            pass
            
        mock_cap.release.assert_called_once()

    @patch("cv2.VideoCapture")
    def test_gui_duration_check_releases_handle(self, mock_cap_cls):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.return_value = 24.0
        mock_cap_cls.return_value = mock_cap
        
        gui_gen = scenepack_generator_gui.ScenePackGenerator(log_queue=MagicMock(), frame_skip=15)
        dur = gui_gen._get_video_duration(Path("dummy_gui_path.mp4"))
        
        mock_cap.release.assert_called_once()


class TestProcessCancellationTracking(unittest.TestCase):
    """Verifies that active FFmpeg subprocesses are tracked and terminated upon cancellation."""
    
    @patch("subprocess.Popen")
    def test_active_subprocess_termination(self, mock_popen):
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc
        
        gui_gen = scenepack_generator_gui.ScenePackGenerator(log_queue=MagicMock(), frame_skip=15)
        self.assertTrue(hasattr(gui_gen, "register_subprocess"), "Must have register_subprocess method")
        self.assertTrue(hasattr(gui_gen, "terminate_all_subprocesses"), "Must have terminate_all_subprocesses method")
        
        gui_gen.register_subprocess(mock_proc)
        self.assertIn(mock_proc, gui_gen._active_subprocesses)
        
        gui_gen.terminate_all_subprocesses()
        mock_proc.terminate.assert_called_once()
        self.assertEqual(len(gui_gen._active_subprocesses), 0)


if __name__ == "__main__":
    unittest.main()
