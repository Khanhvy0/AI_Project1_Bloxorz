"""Kiểm tra form kế thừa chung và tích hợp TV2/TV3 với hai backend graph."""

from pathlib import Path
import tracemalloc
import unittest
from unittest.mock import patch

from game import engine, Direction, MoveStatus, Orient, State, Tile
from game.level import Level, load_level
from solvers.bfs import BFSSovler
from solvers.dfs import DFSSovler, IDSSovler
from solvers.ucs import UCSovler
from solvers.astar import AStarSovler
from solvers.utils.engine_graph import ACTION_TO_DIRECTION, EngineGraph
from solvers.utils.graph import MazeGraph
from solvers.utils.searches import (
    bfs_search, dfs_search, ucs_search, a_star_search, ids_search, l1_heuristic,
)
from solvers.utils.sovler import SolverBaseModel, SolverResult
from utils.measure import measure


CLASSES = (BFSSovler, DFSSovler, UCSovler, AStarSovler, IDSSovler)
LEVELS = Path(__file__).resolve().parents[1] / "levels"
SPLIT_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "tv2_split"


def numbered_levels(first, last):
    return [LEVELS / f"level_{number:02}.json" for number in range(first, last + 1)]


class CommonSolverTests(unittest.TestCase):
    def graphs(self, grid):
        data = {"name": "integration", "grid": grid}
        return (MazeGraph(data), EngineGraph(Level.from_dict(data)))

    def assert_replay(self, graph, result):
        self.assertIsInstance(result, SolverResult)
        self.assertTrue(result.solved)
        self.assertEqual(result.solution_length, len(result.actions))
        state = graph.start_state
        cost = 0.0
        for action in result.actions:
            if isinstance(graph, EngineGraph):
                direction = ACTION_TO_DIRECTION[action]
                move = engine.apply_move(graph.level, state, direction)
                self.assertTrue(move.legal)
                cost += engine.cost(graph.level, state, direction, move.state)
                state = move.state
            else:
                transitions = {move: (nxt, step) for move, nxt, step in graph.get_neighbors(state)}
                self.assertIn(action, transitions)
                state, step = transitions[action]
                cost += step
        self.assertTrue(graph.is_goal(state))
        self.assertEqual(result.solution_cost, cost)

    def test_all_classes_share_parent_and_result(self):
        for graph in self.graphs(["S...", "....", "...G"]):
            for cls in CLASSES:
                with self.subTest(graph=type(graph).__name__, solver=cls.__name__):
                    solver = cls(graph)
                    self.assertIsInstance(solver, SolverBaseModel)
                    result = solver.search()
                    self.assert_replay(graph, result)
                    self.assertGreaterEqual(result.search_time_ms, 0)
                    self.assertGreater(result.peak_memory_kb, 0)
                    if cls is not DFSSovler:
                        self.assertEqual(result.solution_length, 4)

    def test_empty_path_distinguishes_failure_from_initial_goal(self):
        for graph in self.graphs(["S.G"]):
            for cls in CLASSES:
                with self.subTest(graph=type(graph).__name__, solver=cls.__name__):
                    solver = cls(graph, max_depth=4) if cls is IDSSovler else cls(graph)
                    result = solver.solve()
                    self.assertFalse(result.solved)
                    self.assertEqual(result.actions, [])
                    self.assertEqual(result.solution_length, -1)
                    self.assertEqual(result.solution_cost, 0.0)
        for graph in self.graphs(["S..G"]):
            if isinstance(graph, EngineGraph):
                graph.level.goal = graph.level.start
                graph.goal_pos = graph.level.goal
            else:
                graph.goal_pos = (0, 0)
            for cls in CLASSES:
                with self.subTest(graph=type(graph).__name__, solver=cls.__name__):
                    result = cls(graph).solve()
                    self.assertTrue(result.solved)
                    self.assertEqual(result.actions, [])
                    self.assertEqual(result.solution_length, 0)
                    self.assertEqual(result.expanded_nodes, 0)

    def test_expanded_means_non_goal_pop_followed_by_neighbors(self):
        for search in (bfs_search, dfs_search, ucs_search, a_star_search, ids_search):
            with self.subTest(search=search.__name__):
                graph = MazeGraph({"grid": ["S...", "....", "...G"]})
                original = graph.get_neighbors
                expanded_states = []

                def neighbors(state):
                    expanded_states.append(state)
                    return original(state)

                graph.get_neighbors = neighbors
                actions, expanded = search(graph)
                self.assertTrue(actions)
                self.assertEqual(expanded, len(expanded_states))
                self.assertTrue(all(not graph.is_goal(s) for s in expanded_states))
                if search is ucs_search:
                    self.assertEqual(expanded, 15)

    def test_base_measurement_runs_are_separate(self):
        graph = MazeGraph({"grid": ["S..G"]})
        calls = []

        def search(graph):
            calls.append(tracemalloc.is_tracing())
            return ["R", "R"], 2

        solver = SolverBaseModel(graph, search)
        self.assert_replay(graph, solver.solve())
        self.assertEqual(calls, [False, True])
        for target in (solver, solver.search, solver.solve):
            calls.clear()
            report = measure(target, repeats=3)
            self.assertEqual(calls, [False, False, False, True])
            self.assertTrue(report["solved"])
            self.assertEqual(report["length"], 2)

    def test_ucs_prefers_lower_cost_over_fewer_steps(self):
        class WeightedGraph:
            name = "weighted"
            start_state = "start"

            def is_goal(self, state):
                return state == "goal"

            def get_neighbors(self, state):
                return {
                    "start": [("R", "goal", 10.0), ("D", "a", 1.0)],
                    "a": [("R", "b", 1.0)],
                    "b": [("U", "goal", 1.0)],
                }.get(state, [])

        graph = WeightedGraph()
        bfs, ucs = BFSSovler(graph).solve(), UCSovler(graph).solve()
        self.assert_replay(graph, ucs)
        self.assertEqual(bfs.solution_cost, 10)
        self.assertEqual(ucs.solution_cost, 3)
        self.assertEqual(ucs.actions, ["D", "R", "U"])

    def test_l1_does_not_overestimate_a_single_roll(self):
        graph = MazeGraph({"grid": ["S..G"]})
        lying = graph.get_neighbors(graph.start_state)[0][1]
        self.assertLessEqual(l1_heuristic(lying, graph.goal_pos), 1.0)

    def test_basic_and_fragile_levels_across_backends(self):
        for file in sorted(LEVELS.glob("level_*.json")):
            if load_level(str(file)).switch_at:
                continue
            lengths = []
            for graph in (MazeGraph.from_json_file(str(file)), EngineGraph(load_level(str(file)))):
                with self.subTest(level=file.name, graph=type(graph).__name__):
                    bfs = BFSSovler(graph).solve()
                    lengths.append(bfs.solution_length)
                    self.assert_replay(graph, bfs)
                    ucs = UCSovler(graph).solve()
                    self.assert_replay(graph, ucs)
                    for heuristic in ("l1", "l2"):
                        astar = AStarSovler(graph, heuristic=heuristic).solve()
                        self.assert_replay(graph, astar)
                        self.assertEqual(astar.solution_cost, ucs.solution_cost)
            self.assertEqual(lengths[0], lengths[1])

    def test_switch_levels_with_tv3_graph(self):
        # Bộ màn chính không còn split; các tình huống split được giữ trong fixtures.
        for file in sorted(LEVELS.glob("level_*.json")):
            if not load_level(str(file)).switch_at:
                continue
            with self.subTest(level=file.name):
                graph = MazeGraph.from_json_file(str(file))
                self.assert_replay(graph, BFSSovler(graph).solve())
                ucs = UCSovler(graph).solve()
                self.assert_replay(graph, ucs)
                astar = AStarSovler(graph).solve()
                self.assert_replay(graph, astar)
                self.assertEqual(astar.solution_cost, ucs.solution_cost)

    def test_all_levels_with_four_solvers_and_real_replay(self):
        for file in sorted(LEVELS.glob("level_*.json")):
            graph = EngineGraph(load_level(str(file)))
            results = {}
            for cls in CLASSES[:4]:
                with self.subTest(level=file.name, solver=cls.__name__):
                    result = cls(graph).solve()
                    self.assert_replay(graph, result)
                    results[cls] = result
            self.assertEqual(results[BFSSovler].solution_length, results[UCSovler].solution_length)
            self.assertEqual(results[AStarSovler].solution_cost, results[UCSovler].solution_cost)
        graph = EngineGraph(load_level(str(LEVELS / "edge_cases/g1_00_nosol.json")))
        for cls in CLASSES[:4]:
            with self.subTest(solver=cls.__name__):
                result = cls(graph).solve()
                self.assertFalse(result.solved)
                self.assertEqual(result.solution_length, -1)

    def test_ids_matches_bfs_on_each_group(self):
        files = [LEVELS / f"level_{n:02}.json" for n in (1, 2, 4, 7, 16, 19, 20, 21)]
        files += sorted(SPLIT_FIXTURES.glob("*.json"))
        for file in files:
            with self.subTest(level=str(file)):
                graph = EngineGraph(load_level(str(file)))
                bfs = BFSSovler(graph).solve()
                ids = IDSSovler(graph, max_depth=bfs.solution_length).solve()
                self.assert_replay(graph, ids)
                self.assertEqual(ids.solution_length, bfs.solution_length)

    def test_split_level_requires_control_switch_and_replays_events(self):
        graph = EngineGraph(load_level(str(SPLIT_FIXTURES / "level_21.json")))
        result = BFSSovler(graph).solve()
        self.assert_replay(graph, result)
        self.assertIn("SWITCH", result.actions)
        self.assertEqual(result.solution_cost, len(result.actions))
        state, events, touched = graph.start_state, [], set()
        for action in result.actions:
            move = engine.apply_move(graph.level, state, ACTION_TO_DIRECTION[action])
            state = move.state
            events.extend(move.events)
            touched.update(graph.level.tile_at(cell) for cell in state.cells())
        self.assertTrue({"split", "switch_control", "switch", "merge"} <= set(events))
        self.assertTrue({Tile.FRAGILE, Tile.BRIDGE} <= touched)
        neighbors = graph.get_neighbors
        with patch.object(graph, "get_neighbors", side_effect=lambda s: [
            edge for edge in neighbors(s) if edge[0] != "SWITCH"
        ]):
            self.assertFalse(BFSSovler(graph).solve().solved)

    def test_astar_teleport_fallback_covers_the_entire_search(self):
        files = [SPLIT_FIXTURES / "level_21.json", LEVELS.parent / "tests/fixtures/level_10.json"]
        for file in files:
            graph = EngineGraph(load_level(str(file)))
            ucs = UCSovler(graph).solve()
            for heuristic in ("l1", "l2"):
                with self.subTest(level=file.name, heuristic=heuristic):
                    with patch.dict("solvers.utils.searches.heuristic_dict", {
                        heuristic: lambda *_: self.fail("Heuristic khoang cach khong hop le voi teleport")
                    }):
                        astar = AStarSovler(graph, heuristic=heuristic).solve()
                    self.assert_replay(graph, astar)
                    self.assertEqual(astar.solution_cost, ucs.solution_cost)
                    self.assertEqual(astar.expanded_nodes, ucs.expanded_nodes)

    def test_adapter_excludes_moves_that_break_support(self):
        level = Level.from_dict({
            "grid": ["S=o..", ".....", "....G"],
            "bridges": {"b1": {"cells": [[0, 1]], "open": True}},
            "switches": [{"pos": [0, 2], "type": "soft", "targets": ["b1"], "mode": "toggle"}],
        })
        fragile = Level.from_dict({"grid": ["S..F.G"]})
        cases = (
            (level, engine.initial_state(level), MoveStatus.FALL_VOID),
            (fragile, State(0, 1, Orient.HORIZ), MoveStatus.FRAGILE_BREAK),
            (level, State.make_split((0, 1), (1, 2), (1, 2), 1), MoveStatus.FALL_VOID),
        )
        for lv, state, expected in cases:
            direction = Direction.UP if state.is_split else Direction.RIGHT
            action = "U" if state.is_split else "R"
            with self.subTest(state=state):
                self.assertEqual(engine.apply_move(lv, state, direction).status, expected)
                self.assertNotIn(action, [a for a, _, _ in EngineGraph(lv).get_neighbors(state)])


if __name__ == "__main__":
    unittest.main()
