"""Bằng chứng cho báo cáo: với hàm chi phí đã chốt, UCS/A* có thể chọn đường DÀI HƠN về số bước
nhưng RẺ HƠN về chi phí so với BFS (tránh ô fragile). Màn: tests/fixtures/fragile_detour.json."""
import os
import unittest

from game import load_level
from game.analysis import replay_cost

FX = os.path.join(os.path.dirname(__file__), "fixtures", "fragile_detour.json")


class UcsVersusBfs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import solvers.astar as astar
            import solvers.bfs as bfs
            import solvers.ucs as ucs
        except ImportError as e:
            raise unittest.SkipTest(f"chưa có solver: {e}")
        cls.level = load_level(FX)
        cls.bfs, cls.ucs, cls.astar = (staticmethod(m.solve) for m in (bfs, ucs, astar))

    def run_solver(self, solve, **kw):
        path, _ = solve(self.level, **kw)
        return len(path), replay_cost(self.level, path)[0]

    def test_ucs_trades_steps_for_cost(self):
        bfs_steps, bfs_cost = self.run_solver(self.bfs)
        ucs_steps, ucs_cost = self.run_solver(self.ucs)
        self.assertGreater(ucs_steps, bfs_steps, "UCS phải đi nhiều bước hơn BFS ở màn này")
        self.assertLess(ucs_cost, bfs_cost, "UCS phải rẻ hơn BFS ở màn này")
        self.assertEqual((bfs_steps, bfs_cost, ucs_steps, ucs_cost), (9, 15.0, 10, 12.0))

    def test_astar_matches_ucs_cost(self):
        _, ucs_cost = self.run_solver(self.ucs)
        for h in ("pose", "l1", "l2", "chebyshev"):
            with self.subTest(heuristic=h):
                self.assertEqual(self.run_solver(self.astar, heuristic=h)[1], ucs_cost)


if __name__ == "__main__":
    unittest.main()
