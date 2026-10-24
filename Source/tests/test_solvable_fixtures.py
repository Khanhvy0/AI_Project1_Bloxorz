"""Màn mẫu có công tắc/split: BFS giải được và lời giải chạy lại đúng bằng apply_move."""
import os, unittest
from game import MoveStatus, load_level
from tests.helpers import bfs_path, replay

FX = os.path.join(os.path.dirname(__file__), "fixtures")


class Fixtures(unittest.TestCase):
    def solve(self, name):
        lv = load_level(os.path.join(FX, name))
        path = bfs_path(lv)
        self.assertIsNotNone(path, f"{name} không giải được")
        final, status, events = replay(lv, path)
        self.assertEqual(status, MoveStatus.WIN)
        return path, events

    def test_islands_needs_both_switches(self):
        path, events = self.solve("level_09.json")
        self.assertGreaterEqual(events.count("switch"), 2)

    def test_toggle_level(self):
        self.solve("level_08.json")

    def test_split_level_uses_split_and_merge(self):
        path, events = self.solve("level_10.json")
        self.assertIn("split", events)
        self.assertIn("merge", events)

    def test_bridges_are_part_of_state(self):
        """Cùng vị trí khối nhưng khác cầu phải là hai state khác nhau, BFS vẫn giải được."""
        from game import initial_state, State
        lv = load_level(os.path.join(FX, "level_09.json"))
        s = initial_state(lv)
        self.assertNotEqual(s, s._replace(bridges=s.bridges | 1))


if __name__ == "__main__":
    unittest.main()
