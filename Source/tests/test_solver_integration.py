from pathlib import Path
import tracemalloc
import unittest

from game.level import Level, load_level
from game.state import Direction
from game.engine import initial_state
from solvers.bfs import BFSSovler
from solvers.dfs import DFSSovler, IDSSovler
from solvers.ucs import UCSovler
from solvers.astar import AStarSovler
from solvers.utils.searches import (
    bfs_search, dfs_search, ucs_search, a_star_search, l1_heuristic,
)
from game.state import ACTION_TO_DIRECTION
from solvers.utils.solver import SolverBaseModel, SolverResult
from utils.measure import measure

CLASSES = (BFSSovler, DFSSovler, UCSovler, AStarSovler, IDSSovler)
LEVELS = Path(__file__).resolve().parents[1] / "levels"

def numbered_levels(first, last):
    return [LEVELS / f"level_{number:02}.json" for number in range(first, last + 1)]

class CommonSolverTests(unittest.TestCase):
    def levels(self, grid):
        data = {"name": "integration", "grid": grid}
        return (Level.from_dict(data),)

    def assert_replay(self, level, result):
        self.assertIsInstance(result, SolverResult)
        self.assertTrue(result.solved)
        self.assertEqual(result.solution_length, len(result.actions))
        
        from game.engine import get_successors, cost, is_goal
        state = initial_state(level)
        total_cost = 0.0
        
        for action_str in result.actions:
            direction = ACTION_TO_DIRECTION[action_str]
            # Lấy tất cả trạng thái tiếp theo hợp lệ từ engine
            transitions = {d: nxt for d, nxt in get_successors(level, state)}
            self.assertIn(direction, transitions, f"Nước đi {action_str} không hợp lệ tại {state}")
            
            next_state = transitions[direction]
            step = cost(level, state, direction, next_state)
            total_cost += step
            state = next_state
            
        self.assertTrue(is_goal(level, state), "Đường đi không dẫn tới đích")
        self.assertEqual(result.solution_cost, total_cost)

    def test_all_classes_share_parent_and_result(self):
        for level in self.levels(["S...", "....", "...G"]):
            for cls in CLASSES:
                with self.subTest(solver=cls.__name__):
                    solver = cls(level)
                    self.assertIsInstance(solver, SolverBaseModel)
                    result = solver.search()
                    self.assert_replay(level, result)
                    self.assertGreaterEqual(result.search_time_ms, 0)
                    self.assertGreater(result.peak_memory_kb, 0)
                    if cls is not DFSSovler:
                        self.assertEqual(result.solution_length, 4)

    def test_empty_path_distinguishes_failure_from_initial_goal(self):
        for level in self.levels(["S.G"]):
            for cls in CLASSES:
                with self.subTest(solver=cls.__name__):
                    solver = cls(level, max_depth=4) if cls is IDSSovler else cls(level)
                    result = solver.solve()
                    self.assertFalse(result.solved)
                    self.assertEqual(result.actions, [])
                    self.assertEqual(result.solution_length, -1)
                    self.assertEqual(result.solution_cost, 0.0)
                    
        for level in self.levels(["S..G"]):
            level.goal = level.start
            for cls in CLASSES:
                with self.subTest(solver=cls.__name__):
                    result = cls(level).solve()
                    self.assertTrue(result.solved)
                    self.assertEqual(result.actions, [])
                    self.assertEqual(result.solution_length, 0)
                    self.assertEqual(result.expanded_nodes, 0)

    def test_expanded_means_non_goal_pop_followed_by_neighbors(self):
        import game.engine as engine
        for search in (bfs_search, dfs_search, ucs_search, a_star_search):
            with self.subTest(search=search.__name__):
                level = Level.from_dict({"name": "test", "grid": ["S...", "....", "...G"]})
                original_get_successors = engine.get_successors
                expanded_states = []

                def mock_get_successors(lvl, state):
                    expanded_states.append(state)
                    return original_get_successors(lvl, state)

                engine.get_successors = mock_get_successors
                try:
                    actions, expanded = search(level)
                    self.assertTrue(actions)
                    self.assertEqual(expanded, len(expanded_states))
                    self.assertTrue(all(not engine.is_goal(level, s) for s in expanded_states))
                    if search is ucs_search:
                        self.assertEqual(expanded, 15)
                finally:
                    engine.get_successors = original_get_successors

    def test_base_measurement_runs_are_separate(self):
        level = Level.from_dict({"name": "test", "grid": ["S..G"]})
        calls = []

        def mock_search(lvl):
            calls.append(tracemalloc.is_tracing())
            # Giả lập đường đi "R", "R" (độ dài 2) cho lưới S..G
            return ["R", "R"], 2

        solver = SolverBaseModel(level, mock_search)
        self.assert_replay(level, solver.solve())
        self.assertEqual(calls, [False, True])
        
        for target in (solver, solver.search, solver.solve):
            calls.clear()
            report = measure(target, repeats=3)
            self.assertEqual(calls, [False, False, False, True])
            self.assertTrue(report["solved"])
            self.assertEqual(report["length"], 2)

    def test_ucs_prefers_lower_cost_over_fewer_steps(self):
        # Tạo level ảo sử dụng engine mock để test UCS
        import game.engine as engine
        
        class MockLevel:
            def __init__(self):
                self.start = (0, 0)
                self.goal = (0, 2)
                self.switch_at = {}
                self.bridge_ids = []
                self.initial_bridges = 0
                
        level = MockLevel()
        
        # Override hàm để giả lập đồ thị có trọng số
        original_initial = engine.initial_state
        original_is_goal = engine.is_goal
        original_get_successors = engine.get_successors
        original_cost = engine.cost
        
        def mock_initial(lvl): return "start"
        def mock_is_goal(lvl, state): return state == "goal"
        def mock_get_successors(lvl, state):
            return {
                "start": [(Direction.RIGHT, "goal"), (Direction.DOWN, "a")],
                "a": [(Direction.RIGHT, "b")],
                "b": [(Direction.UP, "goal")],
            }.get(state, [])
        def mock_cost(lvl, state, d, nxt):
            if state == "start" and nxt == "goal": return 10.0
            if state == "start" and nxt == "a": return 1.0
            if state == "a" and nxt == "b": return 1.0
            if state == "b" and nxt == "goal": return 1.0
            return 1.0
            
        engine.initial_state = mock_initial
        engine.is_goal = mock_is_goal
        engine.get_successors = mock_get_successors
        engine.cost = mock_cost
        
        try:
            bfs = BFSSovler(level).solve()
            ucs = UCSovler(level).solve()
            
            self.assertEqual(bfs.solution_cost, 10.0)
            self.assertEqual(ucs.solution_cost, 3.0)
            self.assertEqual(ucs.actions, ["D", "R", "U"])
        finally:
            engine.initial_state = original_initial
            engine.is_goal = original_is_goal
            engine.get_successors = original_get_successors
            engine.cost = original_cost

    def test_l1_does_not_overestimate_a_single_roll(self):
        level = Level.from_dict({"name": "test", "grid": ["S..G"]})
        start = initial_state(level)
        
        from game.engine import get_successors
        successors = get_successors(level, start)
        lying_state = None
        for d, nxt in successors:
            if d == Direction.RIGHT:
                lying_state = nxt
                break
                
        self.assertIsNotNone(lying_state)
        # Giả sử l1_heuristic trả về số float và goal là (0, 3)
        # 1 bước lăn từ (0,0) ĐỨNG sang (0,1) NẰM
        # Tại (0,1) NẰM, _active_or_anchor_rc là (0,1). L1 = (|0-0| + |1-3|) * 0.25 = 0.5
        self.assertLessEqual(l1_heuristic(lying_state, level.goal), 1.0)

    def test_basic_and_fragile_levels_across_backends(self):
        for file in numbered_levels(1, 7):
            if not file.exists(): continue
            with self.subTest(level=file.name):
                level = load_level(str(file))
                bfs = BFSSovler(level).solve()
                self.assert_replay(level, bfs)
                
                ucs = UCSovler(level).solve()
                self.assert_replay(level, ucs)
                
                for heuristic in ("l1", "l2"):
                    astar = AStarSovler(level, heuristic=heuristic).solve()
                    self.assert_replay(level, astar)
                    self.assertEqual(astar.solution_cost, ucs.solution_cost)

    def test_switch_levels_with_tv3_graph(self):
        for file in numbered_levels(15, 20):
            if not file.exists(): continue
            with self.subTest(level=file.name):
                level = load_level(str(file))
                bfs = BFSSovler(level).solve()
                self.assert_replay(level, bfs)
                
                ucs = UCSovler(level).solve()
                self.assert_replay(level, ucs)
                
                astar = AStarSovler(level).solve()
                self.assert_replay(level, astar)
                self.assertEqual(astar.solution_cost, ucs.solution_cost)


if __name__ == "__main__":
    unittest.main()