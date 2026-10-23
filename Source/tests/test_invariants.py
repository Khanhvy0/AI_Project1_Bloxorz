"""Duyệt TOÀN BỘ không gian trạng thái của mọi màn và kiểm tra các bất biến luôn đúng."""
import glob, os, unittest
from collections import deque
from game import (Tile, load_level, initial_state, get_successors, is_goal, apply_move,
                  Direction, Orient)

ROOT = os.path.join(os.path.dirname(__file__), "..")
FILES = sorted(glob.glob(os.path.join(ROOT, "levels", "*.json")) +
               glob.glob(os.path.join(ROOT, "tests", "fixtures", "*.json")))
LIMIT = 300_000


def all_states(level):
    start = initial_state(level)
    seen, q = {start}, deque([start])
    while q and len(seen) < LIMIT:
        s = q.popleft()
        for _, n in get_successors(level, s):
            if n not in seen:
                seen.add(n)
                q.append(n)
    return seen


class Invariants(unittest.TestCase):
    def test_all_reachable_states_are_valid(self):
        for f in FILES:
            lv = load_level(f)
            name = os.path.basename(f)
            nb = len(lv.bridge_ids)
            for s in all_states(lv):
                with self.subTest(level=name, state=s):
                    cells = s.cells()
                    # 1) mọi ô khối chiếm nằm trong bảng, không phải void, không phải cầu đóng
                    for c in cells:
                        self.assertTrue(lv.in_bounds(c))
                        t = lv.tile_at(c)
                        self.assertNotEqual(t, Tile.VOID)
                        if t == Tile.BRIDGE:
                            self.assertTrue((s.bridges >> lv.cell_to_bridge[c]) & 1)
                    # 2) khối 1x1x2 đứng không bao giờ ở ô fragile
                    if not s.is_split and s.orient == Orient.STAND:
                        self.assertNotEqual(lv.tile_at(cells[0]), Tile.FRAGILE)
                    # 3) bitmask cầu không vượt số cầu
                    self.assertLess(s.bridges, 1 << max(nb, 1))
                    # 4) dạng chuẩn của state split
                    if s.is_split:
                        self.assertLess(s.split[0], s.split[1])
                        self.assertIn(s.active, (0, 1))
                        self.assertEqual((s.r, s.c, s.orient), (-1, -1, Orient.STAND))
                        self.assertGreater(abs(s.split[0][0] - s.split[1][0]) +
                                           abs(s.split[0][1] - s.split[1][1]), 1)  # không kề nhau
                    # 5) goal là trạng thái kết thúc; số successor <= 5
                    succ = get_successors(lv, s)
                    if is_goal(lv, s):
                        self.assertEqual(succ, [])
                    self.assertLessEqual(len(succ), 5)
                    # 6) get_successors khớp apply_move
                    for d, n in succ:
                        self.assertEqual(apply_move(lv, s, d).state, n)

    def test_successors_deterministic(self):
        for f in FILES:
            lv = load_level(f)
            s = initial_state(lv)
            self.assertEqual(get_successors(lv, s), get_successors(lv, s))


if __name__ == "__main__":
    unittest.main()
