import unittest
from threading import Event

from game import Direction, apply_move, initial_state
from gui import engine_adapter
from gui.server import create_app


class GuiEngineAdapterTests(unittest.TestCase):
    def setUp(self):
        self.level = engine_adapter.get_level("level_01")
        self.state = engine_adapter.initial_state(self.level)

    def test_level_one_move_uses_rules_engine_state(self):
        rules_level = engine_adapter.LEVELS["level_01"]
        rules_result = apply_move(rules_level, initial_state(rules_level), Direction.RIGHT)
        result = engine_adapter.apply_move(self.level, self.state, "right")
        self.assertEqual(
            result["blocks"],
            [[list(cell) for cell in rules_result.state.cells()]],
        )
        self.assertEqual(result["status"], "playing")

    def test_falling_move_returns_lost_state_for_animation(self):
        result = engine_adapter.apply_move(self.level, self.state, "up")
        self.assertEqual(result["status"], "lost")
        self.assertEqual(len(result["blocks"][0]), 2)

    def test_solver_rejects_unknown_algorithms(self):
        with self.assertRaisesRegex(ValueError, "Unsupported solver"):
            engine_adapter.solve(self.level, "unknown")

    def test_solver_stops_when_cancellation_is_requested(self):
        cancellation_event = Event()
        cancellation_event.set()
        with self.assertRaises(engine_adapter.SolveCancelled):
            engine_adapter.solve(self.level, "bfs", cancellation_event)

    def test_levels_are_listed_in_numbered_order(self):
        self.assertEqual(
            [item["id"] for item in engine_adapter.list_levels()],
            [f"level_{number:02}" for number in range(1, 22)],
        )

    def test_all_solver_solutions_replay_through_rules_engine(self):
        for algo in ("bfs", "dfs", "ucs", "astar"):
            with self.subTest(algo=algo):
                result = engine_adapter.solve(self.level, algo)
                self.assertIsNotNone(result["path"])
                state = self.state
                for action in result["path"]:
                    state = engine_adapter.apply_move(self.level, state, action)
                self.assertEqual(state["status"], "won")
                self.assertEqual(result["algo"], algo)
                self.assertEqual(result["stats"]["solution_length"], len(result["path"]))

    def test_dfs_is_available_on_levels_eight_through_ten(self):
        for level_id in ("level_08", "level_09", "level_10"):
            with self.subTest(level=level_id):
                level = engine_adapter.get_level(level_id)
                result = engine_adapter.solve(level, "dfs")
                self.assertIsNotNone(result["path"])
                state = engine_adapter.initial_state(level)
                for action in result["path"]:
                    state = engine_adapter.apply_move(level, state, action)
                self.assertEqual(state["status"], "won")

    def test_replacement_levels_replay_without_split_controls(self):
        for level_id in ("level_19", "level_20", "level_21"):
            for algo in ("bfs", "dfs", "ucs", "astar"):
                with self.subTest(level=level_id, algo=algo):
                    level = engine_adapter.get_level(level_id)
                    result = engine_adapter.solve(level, algo)
                    self.assertIsNotNone(result["path"])
                    state = engine_adapter.initial_state(level)
                    for action in result["path"]:
                        self.assertIn(action, ("up", "down", "left", "right"))
                        state = engine_adapter.apply_move(level, state, action)
                        self.assertEqual(len(state["blocks"]), 1)
                    self.assertEqual(state["status"], "won")

    def test_solve_api_accepts_all_solvers(self):
        client = create_app().test_client()
        for algo in ("bfs", "dfs", "ucs", "astar"):
            with self.subTest(algo=algo):
                response = client.post(
                    "/api/solve",
                    json={
                        "level_id": "level_01",
                        "algo": algo,
                        "solve_id": f"test-{algo}",
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()["algo"], algo)


if __name__ == "__main__":
    unittest.main()
