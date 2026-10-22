import unittest

from game import Direction, apply_move, initial_state
from gui import engine_adapter


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

    def test_solver_rejects_unimplemented_algorithms(self):
        with self.assertRaisesRegex(ValueError, "only BFS is available"):
            engine_adapter.solve(self.level, "astar")

    def test_bfs_solution_replays_through_rules_engine(self):
        result = engine_adapter.solve(self.level, "bfs")
        self.assertIsNotNone(result["path"])
        state = self.state
        for action in result["path"]:
            state = engine_adapter.apply_move(self.level, state, action)
        self.assertEqual(state["status"], "won")


if __name__ == "__main__":
    unittest.main()
