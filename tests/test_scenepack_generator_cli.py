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

    def test_json_stream_queue_proxy(self):
        """Verify JsonStreamQueueProxy emits valid JSON lines to stdout."""
        from scenepack_generator import JsonStreamQueueProxy
        import io
        from contextlib import redirect_stdout

        proxy = JsonStreamQueueProxy()
        buf = io.StringIO()
        with redirect_stdout(buf):
            proxy.put(("progress", 0.5, "Testing progress..."))
            proxy.put(("log", "Sample log message"))
            proxy.put(("episode_progress", (1, 10, "Episode 1.mp4", 0.75, 0.075)))
            proxy.put(("error", "Fatal error occurred"))

        output = buf.getvalue().strip().split("\n")
        self.assertEqual(len(output), 4)

        import json
        ev1 = json.loads(output[0])
        self.assertEqual(ev1["type"], "progress")
        self.assertEqual(ev1["val"], 0.5)

        ev2 = json.loads(output[1])
        self.assertEqual(ev2["type"], "log")
        self.assertEqual(ev2["message"], "Sample log message")

        ev3 = json.loads(output[2])
        self.assertEqual(ev3["type"], "episode_progress")
        self.assertEqual(ev3["cur"], 1)
        self.assertEqual(ev3["tot"], 10)

        ev4 = json.loads(output[3])
        self.assertEqual(ev4["type"], "error")
        self.assertEqual(ev4["message"], "Fatal error occurred")


if __name__ == "__main__":
    unittest.main()
