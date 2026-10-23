"""Test TV2 với engine thật. Chạy từ Source: python -m unittest tests.test_solvers_tv2 -v."""

from dataclasses import replace
from pathlib import Path
import tracemalloc
import unittest
from unittest.mock import patch

from game import engine
from game.level import Level, load_level
from game.state import Direction as D, Orient, State
from solvers.bfs import solve as bfs_solve
from solvers.dfs import solve as dfs_solve, solve_ids
from utils.measure import measure


LEVELS_DIR = Path(__file__).resolve().parents[1] / "levels"
SOLVERS = (bfs_solve, dfs_solve, solve_ids)
STATS_KEYS = {"time_ms", "memory_kb", "expanded_nodes", "solution_length", "solution_cost"}


def make_level(grid):
    return Level.from_dict({"name": "test", "grid": grid})


class SolverTests(unittest.TestCase):
    def assert_solution(self, level, path, stats):
        self.assertIsNotNone(path)
        state = engine.initial_state(level)
        total_cost = 0.0
        for direction in path:
            self.assertIsInstance(direction, D)
            result = engine.apply_move(level, state, direction)
            self.assertTrue(result.legal)
            total_cost += engine.cost(level, state, direction, result.state)
            state = result.state
        self.assertTrue(engine.is_goal(level, state))
        self.assertEqual(set(stats), STATS_KEYS)
        self.assertEqual(stats["solution_length"], len(path))
        self.assertEqual(stats["solution_cost"], total_cost)
        self.assertGreaterEqual(stats["time_ms"], 0)
        self.assertGreater(stats["memory_kb"], 0)

    def test_sanity_bfs(self):
        level = make_level(["S...", "....", "...G"])
        path, stats = bfs_solve(level)
        self.assert_solution(level, path, stats)
        self.assertEqual(path, [D.RIGHT, D.DOWN, D.DOWN, D.RIGHT])
        self.assertEqual(stats["expanded_nodes"], 15)

    def test_dfs_and_ids(self):
        level = make_level(["S...", "....", "...G"])
        for solver in (dfs_solve, solve_ids):
            with self.subTest(solver=solver.__name__):
                path, stats = solver(level)
                self.assert_solution(level, path, stats)
                self.assertGreaterEqual(len(path), 4)
                if solver is solve_ids:
                    self.assertEqual(len(path), 4)

    def test_unsolvable(self):
        for grid in (["S.#", "#.#", "#.G"], ["S.G"]):
            for solver in SOLVERS:
                with self.subTest(grid=grid, solver=solver.__name__):
                    level = make_level(grid)
                    if solver is solve_ids:
                        path, stats = solver(level, max_depth=8)
                    else:
                        path, stats = solver(level)
                    self.assertIsNone(path)
                    self.assertEqual(set(stats), STATS_KEYS)
                    self.assertEqual(stats["solution_length"], -1)
                    self.assertEqual(stats["solution_cost"], 0.0)

    def test_initial_goal_is_not_expanded(self):
        level = make_level(["S..G"])
        level = replace(level, goal=level.start)
        for solver in SOLVERS:
            with self.subTest(solver=solver.__name__):
                with patch.object(engine, "get_successors", side_effect=AssertionError("expanded goal")):
                    path, stats = solver(level)
                self.assertEqual(path, [])
                self.assertEqual(stats["expanded_nodes"], 0)
                self.assertEqual(stats["solution_length"], 0)
                self.assertEqual(stats["solution_cost"], 0.0)

    def test_weighted_cost_is_reported(self):
        level = make_level(["S...", "....", "...G"])
        with patch.object(engine, "cost", return_value=2.5):
            for solver in SOLVERS:
                with self.subTest(solver=solver.__name__):
                    path, stats = solver(level)
                    self.assert_solution(level, path, stats)
                    self.assertEqual(stats["solution_cost"], 2.5 * len(path))

    def test_full_state_is_used_as_visited_key(self):
        # Cùng vị trí/hướng, khác bridges hoặc split/active phải được duyệt riêng.
        start = State(0, 0, Orient.STAND)
        goal = State(0, 3, Orient.STAND)
        variants = (
            replace(start, bridges=1),
            replace(start, split=((0, 0), (0, 1))),
            replace(start, active=1),
        )
        level = make_level(["S..G"])
        for variant in variants:
            graph = {start: [(D.DOWN, variant)], variant: [(D.RIGHT, goal)]}
            for solver in SOLVERS:
                with self.subTest(variant=variant, solver=solver.__name__):
                    with patch.object(engine, "get_successors", side_effect=lambda lv, s: graph.get(s, [])):
                        path, stats = solver(level)
                    self.assertEqual(path, [D.DOWN, D.RIGHT])
                    self.assertEqual(stats["solution_length"], 2)
        # Đây chỉ là test khóa State, không mô phỏng luật split của Tuần 2.

    def test_ids_allows_a_shorter_revisit(self):
        level = make_level(["S..G"])
        start = engine.initial_state(level)
        a, b, c, d, goal = (State(0, col, Orient.STAND) for col in (1, 2, 4, 5, 3))
        graph = {
            start: [(D.UP, a), (D.DOWN, d)],
            a: [(D.RIGHT, b)],
            b: [(D.RIGHT, c)],
            d: [(D.RIGHT, c)],
            c: [(D.RIGHT, goal)],
        }
        with patch.object(engine, "get_successors", side_effect=lambda lv, s: graph.get(s, [])):
            path, stats = solve_ids(level, max_depth=3)
        self.assertEqual(path, [D.DOWN, D.RIGHT, D.RIGHT])
        self.assertEqual(stats["solution_length"], 3)

    def test_ids_depth_limit(self):
        level = make_level(["S...", "....", "...G"])
        path, _ = solve_ids(level, max_depth=3)
        self.assertIsNone(path)
        path, _ = solve_ids(level, max_depth=4)
        self.assertEqual(len(path), 4)
        with self.assertRaises(ValueError):
            solve_ids(level, max_depth=-1)

    def test_dfs_cycle_terminates(self):
        level = make_level(["S.....", "......", ".....G"])
        path, stats = dfs_solve(level)
        self.assert_solution(level, path, stats)
        self.assertLess(stats["expanded_nodes"], 3 * level.rows * level.cols)

    def test_tv2_levels_with_real_engine(self):
        files = [
            *(LEVELS_DIR / f"level_{number:02}.json" for number in range(1, 8)),
            *(LEVELS_DIR / f"level_{number:02}.json" for number in range(15, 21)),
        ]
        self.assertEqual(len(files), 13)
        for file in files:
            with self.subTest(level=file.name):
                level = load_level(str(file))
                # Switch chưa hoạt động: chỉ kiểm tra bố cục với mọi cầu mở.
                if level.switches:
                    level = replace(level, initial_bridges=(1 << len(level.bridge_ids)) - 1)
                path, stats = bfs_solve(level)
                self.assert_solution(level, path, stats)

    def test_unsolvable_level_file(self):
        level = load_level(str(LEVELS_DIR / "edge_cases" / "g1_00_nosol.json"))
        path, stats = bfs_solve(level)
        self.assertIsNone(path)
        self.assertEqual(stats["expanded_nodes"], 1)


class MeasureTests(unittest.TestCase):
    def test_report_uses_standard_solver_stats(self):
        level = make_level(["S...", "....", "...G"])
        result = measure(bfs_solve, level, algorithm="BFS", repeats=2)
        self.assertEqual(set(result), {
            "level", "algorithm", "solved", "time_s", "peak_mem_kb", "expanded", "length"
        })
        self.assertEqual(result["level"], "test")
        self.assertEqual(result["algorithm"], "BFS")
        self.assertTrue(result["solved"])
        self.assertEqual(result["length"], 4)
        self.assertEqual(result["expanded"], 15)

    def test_time_and_memory_runs_are_separate(self):
        calls = []

        def other_solver(level):
            calls.append(tracemalloc.is_tracing())
            return [D.RIGHT], {"expanded_nodes": 1, "solution_cost": 7.0}

        measure(other_solver, make_level(["S..G"]), repeats=3)
        self.assertEqual(calls, [False, False, False, True])

    def test_decorated_search_is_not_measured_twice(self):
        level = make_level(["S...", "....", "...G"])
        calls = []
        raw_search = bfs_solve.__wrapped__

        def search(lv):
            calls.append(tracemalloc.is_tracing())
            return raw_search(lv)

        with patch.object(bfs_solve, "__wrapped__", side_effect=search):
            measure(bfs_solve, level, repeats=2)
        self.assertEqual(calls, [False, False, True])

    def test_unsolvable_report(self):
        result = measure(dfs_solve, make_level(["S.G"]))
        self.assertFalse(result["solved"])
        self.assertEqual(result["length"], -1)

    def test_invalid_repeats(self):
        for repeats in (0, -1, 1.5, True):
            with self.subTest(repeats=repeats):
                with self.assertRaises(ValueError):
                    measure(bfs_solve, make_level(["S..G"]), repeats=repeats)

    def test_tracemalloc_cleanup_on_error(self):
        def failing_solver(level):
            if tracemalloc.is_tracing():
                raise RuntimeError("memory run failed")
            return None, {"expanded_nodes": 1, "solution_cost": 0.0}

        with self.assertRaisesRegex(RuntimeError, "memory run failed"):
            measure(failing_solver, make_level(["S..G"]))
        self.assertFalse(tracemalloc.is_tracing())

    def test_existing_tracer_is_preserved(self):
        tracemalloc.start()
        try:
            with self.assertRaises(RuntimeError):
                measure(bfs_solve, make_level(["S..G"]))
            self.assertTrue(tracemalloc.is_tracing())
        finally:
            tracemalloc.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
