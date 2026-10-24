"""Split switch: dịch chuyển + tách, điều khiển từng khối, ghép lại."""
import unittest
from game import (Level, State, Orient, Direction, MoveStatus, apply_move, get_successors,
                  is_goal, initial_state)

O, D = Orient, Direction

GRID = [
    "S.s.....",
    "...o..x.",
    "...F....",
    "...=.=.G",
]
LV = Level.from_dict({
    "name": "split_test", "grid": GRID,
    "bridges": {"b1": {"cells": [[3, 3]], "open": False},     # bit 0, soft điều khiển
                "b2": {"cells": [[3, 5]], "open": False}},    # bit 1, heavy điều khiển
    "switches": [
        {"pos": [0, 2], "type": "split", "cubes": [[2, 1], [2, 5]]},
        {"pos": [1, 3], "type": "soft", "targets": ["b1"], "mode": "toggle"},
        {"pos": [1, 6], "type": "heavy", "targets": ["b2"], "mode": "toggle"}]})


def split(a, b, active, bridges=0):
    return State.make_split(a, b, active, bridges)


class SplitActivation(unittest.TestCase):
    def test_standing_on_split_teleports_and_splits(self):
        res = apply_move(LV, State(0, 0, O.HORIZ, 0), D.RIGHT)       # đứng lên (0,2)
        self.assertEqual(res.status, MoveStatus.OK)
        self.assertTrue(res.state.is_split)
        self.assertEqual(res.state.split, ((2, 1), (2, 5)))
        self.assertEqual(res.state.active_cell, (2, 1))
        self.assertEqual((res.state.r, res.state.c), (-1, -1))
        self.assertIn("split", res.events)

    def test_lying_on_split_does_not_split(self):
        res = apply_move(LV, State(0, 0, O.STAND, 0), D.RIGHT)       # nằm qua (0,2)
        self.assertFalse(res.state.is_split)

    def test_split_keeps_bridges(self):
        res = apply_move(LV, State(0, 0, O.HORIZ, 2), D.RIGHT)
        self.assertEqual(res.state.bridges, 2)


class SplitControl(unittest.TestCase):
    def setUp(self):
        self.s = split((2, 1), (2, 5), (2, 1))

    def test_switch_control_flips_active(self):
        res = apply_move(LV, self.s, D.SWITCH)
        self.assertEqual(res.state.active_cell, (2, 5))
        self.assertEqual(res.state.split, self.s.split)
        self.assertEqual(apply_move(LV, res.state, D.SWITCH).state, self.s)

    def test_switch_when_not_split_is_blocked_not_fatal(self):
        res = apply_move(LV, initial_state(LV), D.SWITCH)
        self.assertEqual(res.status, MoveStatus.BLOCKED)
        self.assertFalse(res.legal)
        self.assertFalse(res.fatal)

    def test_cube_moves_one_cell(self):
        res = apply_move(LV, self.s, D.RIGHT)
        self.assertEqual(res.state, split((2, 2), (2, 5), (2, 2)))
        # khối không active đứng yên
        self.assertEqual(res.state.split, ((2, 2), (2, 5)))

    def test_canonical_state(self):
        self.assertEqual(split((2, 5), (2, 1), (2, 1)), split((2, 1), (2, 5), (2, 1)))
        self.assertNotEqual(split((2, 1), (2, 5), (2, 1)), split((2, 1), (2, 5), (2, 5)))
        # hai đường đi khác nhau tới cùng cấu hình vật lý phải ra cùng state
        a = apply_move(LV, apply_move(LV, self.s, D.RIGHT).state, D.SWITCH).state
        b = apply_move(LV, apply_move(LV, self.s, D.SWITCH).state, D.SWITCH).state
        b = apply_move(LV, b, D.RIGHT).state
        b = apply_move(LV, b, D.SWITCH).state
        self.assertEqual(a, b)

    def test_successors_in_split_mode(self):
        dirs = {d for d, _ in get_successors(LV, self.s)}
        self.assertEqual(dirs, {D.UP, D.DOWN, D.LEFT, D.RIGHT, D.SWITCH})

    def test_no_switch_in_normal_mode(self):
        dirs = {d for d, _ in get_successors(LV, initial_state(LV))}
        self.assertNotIn(D.SWITCH, dirs)


class SplitMerge(unittest.TestCase):
    def test_horizontal_merge(self):
        s = split((2, 1), (2, 3), (2, 3))        # (2,3) là ô fragile: khối nhỏ đứng được
        res = apply_move(LV, s, D.LEFT)          # (2,2) kề (2,1)
        self.assertEqual(res.status, MoveStatus.OK)
        self.assertEqual(res.state, State(2, 1, O.HORIZ, 0))
        self.assertIn("merge", res.events)

    def test_vertical_merge(self):
        s = split((1, 4), (3, 4), (3, 4))
        res = apply_move(LV, s, D.UP)            # (2,4) kề (1,4)
        self.assertEqual(res.state, State(1, 4, O.VERT, 0))

    def test_merge_from_either_side(self):
        s = split((2, 1), (2, 3), (2, 1))
        res = apply_move(LV, s, D.RIGHT)          # (2,2) kề (2,3): khối chiếm (2,2),(2,3)
        self.assertEqual(res.state, State(2, 2, O.HORIZ, 0))
        self.assertFalse(res.state.is_split)

    def test_merged_block_continues_normally(self):
        s = State(2, 1, O.HORIZ, 0)
        res = apply_move(LV, s, D.RIGHT)         # HORIZ lăn phải -> đứng ở (2,3) = fragile -> vỡ
        self.assertEqual(res.status, MoveStatus.FRAGILE_BREAK)

    def test_merge_state_equals_plain_state(self):
        self.assertEqual(State(2, 1, O.HORIZ, 0), State(2, 1, O.HORIZ))


class CubeRules(unittest.TestCase):
    def test_cube_on_fragile_is_safe(self):
        res = apply_move(LV, split((2, 1), (0, 6), (2, 2)), D.RIGHT)   # vào (2,3) fragile
        self.assertEqual(res.status, MoveStatus.OK)

    def test_cube_triggers_soft(self):
        res = apply_move(LV, split((1, 2), (2, 5), (1, 2)), D.RIGHT)   # (1,3) soft -> b1
        self.assertEqual(res.state.bridges, 1)
        self.assertIn("switch", res.events)

    def test_cube_cannot_trigger_heavy(self):
        res = apply_move(LV, split((1, 5), (2, 1), (1, 5)), D.RIGHT)   # (1,6) heavy
        self.assertEqual(res.status, MoveStatus.OK)
        self.assertEqual(res.state.bridges, 0)

    def test_cube_cannot_trigger_split(self):
        res = apply_move(LV, split((0, 1), (2, 5), (0, 1)), D.RIGHT)   # (0,2) split
        self.assertTrue(res.state.is_split)
        self.assertEqual(res.state.split, ((0, 2), (2, 5)))

    def test_cube_falls_off_board(self):
        res = apply_move(LV, split((0, 0), (2, 5), (0, 0)), D.UP)
        self.assertEqual(res.status, MoveStatus.FALL_OFF_BOARD)
        self.assertTrue(res.fatal)

    def test_cube_falls_on_closed_bridge(self):
        res = apply_move(LV, split((3, 2), (0, 6), (3, 2)), D.RIGHT)   # (3,3) cầu đóng
        self.assertEqual(res.status, MoveStatus.FALL_VOID)

    def test_cube_closing_bridge_under_other_cube_falls(self):
        # cube kia đứng trên cầu b1 đang mở; cube active bấm soft -> b1 đóng -> cube kia rơi
        s = split((1, 2), (3, 3), (1, 2), bridges=1)
        res = apply_move(LV, s, D.RIGHT)
        self.assertEqual(res.status, MoveStatus.FALL_VOID)

    def test_cube_on_goal_is_not_win(self):
        res = apply_move(LV, split((3, 6), (0, 6), (3, 6)), D.RIGHT)   # vào (3,7) = goal
        self.assertEqual(res.status, MoveStatus.OK)
        self.assertFalse(is_goal(LV, res.state))


class SplitLoader(unittest.TestCase):
    def build(self, **sw):
        base = {"pos": [0, 1], "type": "split", "cubes": [[2, 0], [2, 4]]}
        base.update(sw)
        return Level.from_dict({"grid": ["SsG..", ".....", "....."], "switches": [base]})

    def test_valid(self):
        self.assertIsNotNone(self.build())

    def test_invalid(self):
        from game import LevelError
        bad = [dict(cubes=None), dict(cubes=[[2, 0]]), dict(cubes=[[2, 0], [2, 1]]),
               dict(cubes=[[2, 0], [2, 0]]), dict(cubes=[[2, 0], [9, 9]])]
        for kw in bad:
            with self.subTest(kw=kw), self.assertRaises(LevelError):
                self.build(**kw)

    def test_other_errors(self):
        from game import LevelError
        # ô công tắc chưa khai báo
        with self.assertRaises(LevelError):
            Level.from_dict({"grid": ["SoG"]})
        # mode sai
        with self.assertRaises(LevelError):
            Level.from_dict({"grid": ["SoG.="], "bridges": {"b": {"cells": [[0, 4]]}},
                             "switches": [{"pos": [0, 1], "type": "soft", "targets": ["b"], "mode": "x"}]})
        # thiếu targets
        with self.assertRaises(LevelError):
            Level.from_dict({"grid": ["SoG"], "switches": [{"pos": [0, 1], "type": "soft"}]})
        # trùng ô công tắc
        with self.assertRaises(LevelError):
            Level.from_dict({"grid": ["SoG.="], "bridges": {"b": {"cells": [[0, 4]]}},
                             "switches": [{"pos": [0, 1], "type": "soft", "targets": ["b"]},
                                          {"pos": [0, 1], "type": "soft", "targets": ["b"]}]})


if __name__ == "__main__":
    unittest.main()
