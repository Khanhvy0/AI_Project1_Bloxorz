import glob, os, unittest
from game import Level, LevelError, Tile, load_level
from tests.helpers import bfs_path_length

LEVEL_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class Loader(unittest.TestCase):
    def test_load_basic(self):
        lv = Level.from_dict({"grid": ["S.G", "..."]})
        self.assertEqual((lv.rows, lv.cols), (2, 3))
        self.assertEqual(lv.start, (0, 0))
        self.assertEqual(lv.goal, (0, 2))
        self.assertEqual(lv.tile_at((0, 0)), Tile.FLOOR)
        self.assertEqual(lv.tile_at((0, 2)), Tile.GOAL)

    def test_errors(self):
        bad = [
            {"grid": ["S.", "G"]},                 # không chữ nhật
            {"grid": ["S.."]},                     # thiếu G
            {"grid": ["G.."]},                     # thiếu S
            {"grid": ["SSG"]},                     # 2 ô S
            {"grid": ["S?G"]},                     # ký tự lạ
            {"grid": ["S=G"]},                     # '=' chưa thuộc cầu
            {"grid": ["S.G"], "bridges": {"b": {"cells": [[0, 1]]}}},  # ô cầu không phải '='
            {"grid": ["SoG"], "switches": [{"pos": [0, 1], "type": "heavy"}]},  # sai loại
        ]
        for d in bad:
            with self.assertRaises(LevelError, msg=str(d)):
                Level.from_dict(d)

    def test_fixture_levels_load_and_solvable(self):
        files = sorted(glob.glob(os.path.join(LEVEL_DIR, "*.json")))
        self.assertGreaterEqual(len(files), 3)
        for f in files:
            lv = load_level(f)
            self.assertIsNotNone(bfs_path_length(lv), f"{os.path.basename(f)} không giải được")


if __name__ == "__main__":
    unittest.main()
