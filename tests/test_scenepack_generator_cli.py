import unittest
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scenepack_generator import ScenePackGenerator


class TestCLIScenePackGeneratorLogic(unittest.TestCase):

    def setUp(self):
        self.generator = ScenePackGenerator(frame_skip=15)

    def test_cli_merge_intervals_empty(self):
        result = self.generator.merge_intervals([], padding_before=2.0, padding_after=2.0, duration=100.0)
        self.assertEqual(result, [])

    def test_cli_merge_intervals_single(self):
        result = self.generator.merge_intervals([10.0], padding_before=2.0, padding_after=2.0, duration=100.0)
        self.assertEqual(result, [(8.0, 12.0)])

    def test_cli_merge_intervals_gap_bridging(self):
        result = self.generator.merge_intervals([10.0, 11.0, 12.0], padding_before=2.0, padding_after=2.0, duration=100.0, max_gap_tolerance=1.5)
        self.assertEqual(result, [(8.0, 14.0)])

    def test_cli_merge_intervals_boundary_clamping(self):
        result1 = self.generator.merge_intervals([1.0], padding_before=3.0, padding_after=1.0, duration=100.0)
        self.assertEqual(result1, [(0.0, 2.0)])


if __name__ == "__main__":
    unittest.main()
