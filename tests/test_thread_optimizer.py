import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# If optional computer vision runtime packages are not installed in the local environment,
# provide lightweight test doubles so the backend module loads cleanly.
if "cv2" not in sys.modules:
    try:
        import cv2
    except ImportError:
        sys.modules["cv2"] = MagicMock()
if "numpy" not in sys.modules:
    try:
        import numpy
    except ImportError:
        sys.modules["numpy"] = MagicMock()
if "PIL" not in sys.modules:
    try:
        import PIL
        from PIL import Image, ImageDraw
    except ImportError:
        sys.modules["PIL"] = MagicMock()
        sys.modules["PIL.Image"] = MagicMock()
        sys.modules["PIL.ImageDraw"] = MagicMock()

from scenepack_generator_backend import ThreadOptimizer


class TestThreadOptimizer(unittest.TestCase):
    """
    Comprehensive test suite verifying the dynamic hardware-aware ThreadOptimizer.
    Tests thread allocation across multiple CPU topologies (2, 4, 8, 16, 32, 64 cores),
    low-memory safety throttling, user overrides, and hardware summary telemetry.
    """

    def setUp(self):
        self.ThreadOptimizer = ThreadOptimizer
        self.ThreadOptimizer.set_thread_override(None)
        self.ThreadOptimizer._cached_cpu_cores = None

    def tearDown(self):
        self.ThreadOptimizer.set_thread_override(None)
        self.ThreadOptimizer._cached_cpu_cores = None

    def test_cpu_cores_detection(self):
        cores = self.ThreadOptimizer.get_cpu_cores()
        self.assertIsInstance(cores, int)
        self.assertGreaterEqual(cores, 1)

    def test_available_ram_detection(self):
        ram = self.ThreadOptimizer.get_available_ram_gb()
        self.assertIsInstance(ram, (int, float))
        self.assertGreaterEqual(ram, 0.0)

    def test_scaling_2_cores_laptop(self):
        with patch.object(self.ThreadOptimizer, "get_cpu_cores", return_value=2), \
             patch.object(self.ThreadOptimizer, "get_available_ram_gb", return_value=8.0):
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("cpu_scan"), 1)
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("gallery_scan"), 1)
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("render_hardware"), 2)
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("render_software"), 1)

    def test_scaling_4_cores(self):
        with patch.object(self.ThreadOptimizer, "get_cpu_cores", return_value=4), \
             patch.object(self.ThreadOptimizer, "get_available_ram_gb", return_value=16.0):
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("cpu_scan"), 3)
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("render_hardware"), 4)
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("render_software"), 3)

    def test_scaling_8_cores(self):
        with patch.object(self.ThreadOptimizer, "get_cpu_cores", return_value=8), \
             patch.object(self.ThreadOptimizer, "get_available_ram_gb", return_value=16.0):
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("cpu_scan"), 7)
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("render_hardware"), 4)
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("render_software"), 4)

    def test_scaling_16_cores_workstation(self):
        # i9-11900KF target configuration
        with patch.object(self.ThreadOptimizer, "get_cpu_cores", return_value=16), \
             patch.object(self.ThreadOptimizer, "get_available_ram_gb", return_value=32.0):
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("cpu_scan"), 14)
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("gallery_scan"), 14)
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("render_hardware"), 6)
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("render_software"), 8)

    def test_scaling_32_cores(self):
        with patch.object(self.ThreadOptimizer, "get_cpu_cores", return_value=32), \
             patch.object(self.ThreadOptimizer, "get_available_ram_gb", return_value=64.0):
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("cpu_scan"), 28)
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("render_hardware"), 6)
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("render_software"), 8)

    def test_scaling_64_cores_threadripper(self):
        with patch.object(self.ThreadOptimizer, "get_cpu_cores", return_value=64), \
             patch.object(self.ThreadOptimizer, "get_available_ram_gb", return_value=128.0):
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("cpu_scan"), 32)
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("render_hardware"), 6)
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("render_software"), 8)

    def test_low_ram_throttling(self):
        # Even with 16 cores, if available RAM is < 1.5 GB, throttle to 2 workers to prevent OOM
        with patch.object(self.ThreadOptimizer, "get_cpu_cores", return_value=16), \
             patch.object(self.ThreadOptimizer, "get_available_ram_gb", return_value=1.1):
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("cpu_scan"), 2)

        # If available RAM is between 1.5 GB and 3.0 GB, throttle to 4 workers
        with patch.object(self.ThreadOptimizer, "get_cpu_cores", return_value=16), \
             patch.object(self.ThreadOptimizer, "get_available_ram_gb", return_value=2.2):
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("cpu_scan"), 4)

    def test_user_thread_override(self):
        self.ThreadOptimizer.set_thread_override(5)
        self.assertEqual(self.ThreadOptimizer.get_optimal_threads("cpu_scan"), 5)
        self.assertEqual(self.ThreadOptimizer.get_optimal_threads("render_hardware"), 5)
        self.assertEqual(self.ThreadOptimizer.get_optimal_threads("render_software"), 5)

        # Clear override
        self.ThreadOptimizer.set_thread_override(None)
        with patch.object(self.ThreadOptimizer, "get_cpu_cores", return_value=16), \
             patch.object(self.ThreadOptimizer, "get_available_ram_gb", return_value=32.0):
            self.assertEqual(self.ThreadOptimizer.get_optimal_threads("cpu_scan"), 14)

    def test_hardware_summary_string(self):
        summary = self.ThreadOptimizer.get_hardware_summary()
        self.assertIn("Hardware Topology:", summary)
        self.assertIn("Cores", summary)
        self.assertIn("Scan:", summary)
        self.assertIn("Render (GPU):", summary)


if __name__ == "__main__":
    unittest.main()
