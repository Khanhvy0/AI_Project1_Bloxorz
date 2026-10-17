import unittest
from game import (Level, State, Orient, Direction, MoveStatus, apply_move,
                  get_successors, is_goal, cost, initial_state)

O, D = Orient, Direction


def make(grid, **extra):
    return Level.from_dict({"name": "t", "grid": grid, **extra})


class BasicRules(unittest.TestCase):
    def setUp(self):
        self.lv = make(["S..#.",
                        "...G.",
                        "....."])

    def test_initial_state(self):
        s = initial_state(self.lv)
        self.assertEqual((s.r, s.c, s.orient), (0, 0, O.STAND))

    def test_fall_off_board(self):
        s = initial_state(self.lv)
        self.assertEqual(apply_move(self.lv, s, D.UP).status, MoveStatus.FALL_OFF_BOARD)
        self.assertEqual(apply_move(self.lv, s, D.LEFT).status, MoveStatus.FALL_OFF_BOARD)

    def test_fall_into_void(self):
        s = State(0, 1, O.STAND)  # lăn phải -> chiếm (0,2),(0,3), (0,3) là void
        self.assertEqual(apply_move(self.lv, s, D.RIGHT).status, MoveStatus.FALL_VOID)

    def test_legal_move(self):
        s = initial_state(self.lv)
        res = apply_move(self.lv, s, D.DOWN)
        self.assertTrue(res.legal)
        self.assertEqual(res.state, State(1, 0, O.VERT))

    def test_win_only_when_standing_on_goal(self):
        # nằm ngang qua goal (1,3): KHÔNG thắng
        lying = State(1, 2, O.HORIZ)
        self.assertFalse(is_goal(self.lv, lying))
        # đứng trên goal: thắng. Từ nằm ngang (1,1)-(1,2) lăn phải -> đứng ở (1,3)
        res = apply_move(self.lv, State(1, 1, O.HORIZ), D.RIGHT)
        self.assertEqual(res.status, MoveStatus.WIN)
        self.assertTrue(is_goal(self.lv, res.state))

    def test_lying_across_goal_is_legal(self):
        res = apply_move(self.lv, State(1, 0, O.STAND), D.RIGHT)  # chiếm (1,1),(1,2)
        self.assertEqual(res.status, MoveStatus.OK)
        res = apply_move(self.lv, State(1, 1, O.STAND), D.RIGHT)  # chiếm (1,2),(1,3): nằm qua goal
        self.assertEqual(res.status, MoveStatus.OK)

    def test_goal_is_terminal(self):
        self.assertEqual(get_successors(self.lv, State(1, 3, O.STAND)), [])

    def test_successors_only_legal(self):
        succ = get_successors(self.lv, initial_state(self.lv))
        self.assertEqual({d for d, _ in succ}, {D.DOWN, D.RIGHT})

    def test_cost_default(self):
        s = initial_state(self.lv)
        d, n = get_successors(self.lv, s)[0]
        self.assertEqual(cost(self.lv, s, d, n), 1)


class FragileTiles(unittest.TestCase):
    def setUp(self):
        self.lv = make(["S.F..",
                        "..F..",
                        "....G"])

    def test_standing_on_fragile_breaks(self):
        # từ đứng (0,1), lăn phải -> nằm (0,2),(0,3) : (0,2) fragile nhưng đang nằm -> OK
        self.assertEqual(apply_move(self.lv, State(0, 1, O.STAND), D.RIGHT).status, MoveStatus.OK)
        # từ nằm (0,0)-(0,1), lăn phải -> đứng ở (0,2) = fragile -> vỡ
        self.assertEqual(apply_move(self.lv, State(0, 0, O.HORIZ), D.RIGHT).status,
                         MoveStatus.FRAGILE_BREAK)

    def test_lying_on_fragile_ok(self):
        # nằm dọc (0,2)-(1,2) cả hai ô đều fragile: vẫn an toàn
        res = apply_move(self.lv, State(0, 1, O.VERT), D.RIGHT)
        self.assertEqual(res.status, MoveStatus.OK)


class BridgeTiles(unittest.TestCase):
    GRID = ["S.=..",
            "..=.G"]

    def level(self, is_open):
        return make(self.GRID, bridges={"b1": {"cells": [[0, 2], [1, 2]], "open": is_open}})

    def test_closed_bridge_is_void(self):
        lv = self.level(False)
        s = initial_state(lv)
        self.assertEqual(s.bridges, 0)
        # đứng (0,1) -> lăn phải: chiếm (0,2),(0,3), (0,2) là cầu đóng
        self.assertEqual(apply_move(lv, State(0, 1, O.STAND, 0), D.RIGHT).status, MoveStatus.FALL_VOID)

    def test_open_bridge_is_floor(self):
        lv = self.level(True)
        s = initial_state(lv)
        self.assertEqual(s.bridges, 1)
        self.assertEqual(apply_move(lv, State(0, 1, O.STAND, 1), D.RIGHT).status, MoveStatus.OK)

    def test_bridge_state_distinguishes_states(self):
        self.assertNotEqual(State(0, 0, O.STAND, 0), State(0, 0, O.STAND, 1))

    def test_bridge_bits_preserved_on_move(self):
        lv = self.level(True)
        res = apply_move(lv, State(0, 1, O.STAND, 1), D.RIGHT)
        self.assertEqual(res.state.bridges, 1)

    def test_soft_switch_opens_bridge_when_entered(self):
        lv = make(
            ["S.o=G", "....."],
            bridges={"b1": {"cells": [[0, 3]], "open": False}},
            switches=[{"pos": [0, 2], "type": "soft", "targets": ["b1"], "mode": "open"}],
        )
        result = apply_move(lv, initial_state(lv), D.RIGHT)
        self.assertTrue(result.legal)
        self.assertEqual(result.state.bridges, 1)

    def test_heavy_switch_requires_standing(self):
        lv = make(
            ["S.x..", "...=G"],
            bridges={"b1": {"cells": [[1, 3]], "open": False}},
            switches=[{"pos": [0, 2], "type": "heavy", "targets": ["b1"], "mode": "open"}],
        )
        lying = apply_move(lv, State(0, 1, O.STAND), D.RIGHT)
        self.assertTrue(lying.legal)
        self.assertEqual(lying.state.bridges, 0)

        standing = apply_move(lv, State(0, 3, O.HORIZ), D.LEFT)
        self.assertTrue(standing.legal)
        self.assertEqual(standing.state.bridges, 1)


if __name__ == "__main__":
    unittest.main()
