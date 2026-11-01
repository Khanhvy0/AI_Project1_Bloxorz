"""Hàm chi phí đã chốt: 1.0 bình thường, 2.0 nếu chiếm ô fragile, SWITCH = 1.0."""
import unittest
from game import Level, State, Orient, Direction, apply_move, cost
from game.engine import COST_BASE, COST_FRAGILE, MIN_STEP_COST

O, D = Orient, Direction

def make():
    return Level.from_dict({
        "grid": ["S.F....", ".....o.", "...=.s.", "......G"],
        "bridges": {"b1": {"cells": [[2, 3]], "open": False}},
        "switches": [
            {"pos": [1, 5], "type": "soft", "targets": ["b1"], "mode": "open"},
            {"pos": [2, 5], "type": "split", "cubes": [[3, 0], [3, 3]]},
        ]})


class CostFunction(unittest.TestCase):
    def setUp(self):
        self.lv = make()

    def step(self, s, d):
        res = apply_move(self.lv, s, d)
        self.assertTrue(res.legal, res.status)
        return cost(self.lv, s, d, res.state)

    def test_constants(self):
        self.assertEqual((COST_BASE, COST_FRAGILE, MIN_STEP_COST), (1.0, 2.0, 1.0))

    def test_plain_move(self):
        self.assertEqual(self.step(State(0, 0, O.STAND), D.DOWN), 1.0)

    def test_lying_on_fragile_costs_2(self):
        # đứng (0,0) lăn phải: nằm (0,1),(0,2); (0,2) là fragile
        self.assertEqual(self.step(State(0, 0, O.STAND), D.RIGHT), 2.0)

    def test_one_fragile_cell_is_enough(self):
        # nằm dọc (0,2)-(1,2): hai ô đều fragile? (1,2) là sàn: chỉ cần một ô fragile là 2.0
        self.assertEqual(self.step(State(0, 1, O.VERT), D.RIGHT), 2.0)

    def test_leaving_fragile_is_cheap(self):
        # từ nằm (0,1),(0,2) lăn xuống: nằm (1,1),(1,2): không còn ô fragile
        self.assertEqual(self.step(State(0, 1, O.HORIZ), D.DOWN), 1.0)

    def test_activating_switch_costs_base(self):
        # đứng (1,3) lăn phải: nằm (1,4),(1,5) đè soft switch
        s = State(1, 3, O.STAND)
        res = apply_move(self.lv, s, D.RIGHT)
        self.assertIn("switch", res.events)
        self.assertEqual(cost(self.lv, s, D.RIGHT, res.state), 1.0)

    def test_switch_action_costs_base(self):
        s = State.make_split((3, 0), (3, 3), (3, 0), 0)
        res = apply_move(self.lv, s, D.SWITCH)
        self.assertEqual(cost(self.lv, s, D.SWITCH, res.state), 1.0)

    def test_switch_action_on_fragile_cube_still_base(self):
        lv = Level.from_dict({"grid": ["SFs.G"], "switches": [
            {"pos": [0, 2], "type": "split", "cubes": [[0, 1], [0, 4]]}]})
        s = State.make_split((0, 1), (0, 4), (0, 1), 0)        # khối nhỏ đang đứng trên ô fragile
        res = apply_move(lv, s, D.SWITCH)
        self.assertEqual(cost(lv, s, D.SWITCH, res.state), 1.0)

    def test_cube_stepping_on_fragile_costs_2(self):
        lv = Level.from_dict({"grid": ["S.F..G"], "switches": []})
        s = State.make_split((0, 1), (0, 5), (0, 1), 0)
        res = apply_move(lv, s, D.RIGHT)                         # khối nhỏ bước vào ô fragile (0,2)
        self.assertEqual(cost(lv, s, D.RIGHT, res.state), 2.0)

    def test_every_step_at_least_min_cost(self):
        from game import get_successors, initial_state
        seen, stack = set(), [initial_state(self.lv)]
        while stack:
            s = stack.pop()
            if s in seen:
                continue
            seen.add(s)
            for d, n in get_successors(self.lv, s):
                self.assertGreaterEqual(cost(self.lv, s, d, n), MIN_STEP_COST)
                stack.append(n)


if __name__ == "__main__":
    unittest.main()
