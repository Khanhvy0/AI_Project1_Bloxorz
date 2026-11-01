"""Kiểm tra THỰC NGHIỆM heuristic của A* trên toàn bộ state của mọi màn.

  - admissible : h(s) <= chi phí tối ưu thật từ s tới goal      (với mọi state tới được goal)  -> cả 4 heuristic
  - consistent : h(s) <= c(s, s') + h(s') trên mọi cạnh           -> pose, l1, l2
  - h(goal) = 0 và h >= 0

GHI CHÚ: 'chebyshev' admissible nhưng KHÔNG consistent (đo được 47 cạnh vi phạm trên các màn hiện có,
vd. đứng (0,0) -> nằm (0,1)-(0,2): h giảm 2 trong khi bước tốn 1). Vì a_star_search cho phép mở lại nút khi
tìm được g tốt hơn nên A* với chebyshev vẫn trả về lời giải tối ưu, nhưng báo cáo KHÔNG được nói nó consistent.

Chạy:  python -m unittest tests.test_heuristics -v
Đây là bằng chứng thực nghiệm để đưa vào báo cáo; phần lý thuyết vẫn cần chứng minh bằng lời.
"""
import glob
import os
import unittest

from game import load_level, is_goal
from game.analysis import cost_to_go
from solvers.utils.engine_graph import EngineGraph
from solvers.utils.searches import make_heuristic

HEURISTICS = ("pose", "l1", "l2", "chebyshev")   # admissible
CONSISTENT = ("pose", "l1", "l2")                 # thêm consistent
MAX_STATES = 50_000
ROOT = os.path.join(os.path.dirname(__file__), "..")
FILES = sorted(glob.glob(os.path.join(ROOT, "levels", "*.json")) +
               glob.glob(os.path.join(ROOT, "tests", "fixtures", "*.json")))
EPS = 1e-9


class HeuristicProperties(unittest.TestCase):
    def test_admissible_and_consistent(self):
        checked = 0
        for f in FILES:
            level = load_level(f)
            result = cost_to_go(level, limit=MAX_STATES)
            if result is None:
                continue
            h_star, edges = result
            graph = EngineGraph(level)
            for name in HEURISTICS:
                h = make_heuristic(graph, name)
                with self.subTest(level=os.path.basename(f), heuristic=name):
                    for s, true_cost in h_star.items():
                        hv = h(s, level.goal)
                        self.assertGreaterEqual(hv, 0.0, f"h âm tại {s}")
                        self.assertLessEqual(hv, true_cost + EPS,
                                             f"KHÔNG admissible tại {s}: h={hv} > chi phí thật {true_cost}")
                        if is_goal(level, s):
                            self.assertEqual(hv, 0.0, "h(goal) phải bằng 0")
                    if name not in CONSISTENT:
                        continue
                    for s, c, n in edges:
                        hs, hn = h(s, level.goal), h(n, level.goal)
                        if hs == float("inf") or hn == float("inf"):
                            continue
                        self.assertLessEqual(hs, c + hn + EPS,
                                             f"KHÔNG consistent: h({s})={hs} > {c} + h({n})={hn}")
                    checked += 1
        self.assertGreater(checked, 0, "không có màn nào để kiểm tra")


if __name__ == "__main__":
    unittest.main()
