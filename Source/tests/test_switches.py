"""Soft / heavy switch, toggle / permanent, cầu đóng dưới chân khối."""
import unittest
from game import (Level, State, Orient, Direction, MoveStatus, apply_move, initial_state)

O, D = Orient, Direction


def make(mode="toggle", kind="soft", init_open=False, grid=None, target_cell=(2, 1)):
    ch = {"soft": "o", "heavy": "x"}[kind]
    grid = grid or ["S." + ch + ".G", ".....", ".=..."]
    return Level.from_dict({
        "name": "t", "grid": grid,
        "bridges": {"b1": {"cells": [list(target_cell)], "open": init_open}},
        "switches": [{"pos": [0, 2], "type": kind, "targets": ["b1"], "mode": mode}]})


class SoftSwitch(unittest.TestCase):
    def test_standing_on_soft_toggles(self):
        lv = make()
        res = apply_move(lv, State(0, 0, O.HORIZ, 0), D.RIGHT)       # đứng lên (0,2)
        self.assertEqual(res.state, State(0, 2, O.STAND, 1))
        self.assertIn("switch", res.events)

    def test_lying_on_soft_also_toggles(self):
        lv = make()
        res = apply_move(lv, State(0, 0, O.STAND, 0), D.RIGHT)       # nằm (0,1),(0,2)
        self.assertEqual(res.state, State(0, 1, O.HORIZ, 1))

    def test_toggle_twice_returns(self):
        lv = make()
        s = State(0, 0, O.STAND, 0)
        s = apply_move(lv, s, D.RIGHT).state    # toggle -> 1
        self.assertEqual(s.bridges, 1)
        s = apply_move(lv, s, D.LEFT).state     # đứng lại ở (0,0)
        s = apply_move(lv, s, D.RIGHT).state    # toggle -> 0
        self.assertEqual(s.bridges, 0)

    def test_permanent_open_stays_open(self):
        lv = make(mode="open")
        s = State(0, 0, O.STAND, 0)
        s = apply_move(lv, s, D.RIGHT).state
        s = apply_move(lv, s, D.LEFT).state
        s = apply_move(lv, s, D.RIGHT).state
        self.assertEqual(s.bridges, 1)

    def test_permanent_close_stays_closed(self):
        lv = make(mode="close", init_open=True)
        s = State(0, 0, O.STAND, 1)
        s = apply_move(lv, s, D.RIGHT).state
        self.assertEqual(s.bridges, 0)
        s = apply_move(lv, s, D.LEFT).state
        s = apply_move(lv, s, D.RIGHT).state
        self.assertEqual(s.bridges, 0)

    def test_moving_away_does_not_retrigger(self):
        lv = make()
        s = apply_move(lv, State(0, 0, O.STAND, 0), D.RIGHT).state   # bridges = 1
        s = apply_move(lv, s, D.DOWN).state                          # rời công tắc
        self.assertEqual(s.bridges, 1)


class HeavySwitch(unittest.TestCase):
    def test_lying_does_not_trigger(self):
        lv = make(kind="heavy")
        res = apply_move(lv, State(0, 0, O.STAND, 0), D.RIGHT)       # nằm qua (0,2)
        self.assertEqual(res.state.bridges, 0)
        self.assertNotIn("switch", res.events)

    def test_standing_triggers(self):
        lv = make(kind="heavy")
        res = apply_move(lv, State(0, 0, O.HORIZ, 0), D.RIGHT)       # đứng lên (0,2)
        self.assertEqual(res.state.bridges, 1)
        self.assertIn("switch", res.events)

    def test_heavy_permanent(self):
        lv = make(kind="heavy", mode="open")
        s = apply_move(lv, State(0, 0, O.HORIZ, 0), D.RIGHT).state
        s = apply_move(lv, s, D.LEFT).state     # nằm (0,0)? -> HORIZ(0,1)... rời công tắc
        self.assertEqual(s.bridges, 1)


class Bridges(unittest.TestCase):
    def test_closed_bridge_blocks_open_allows(self):
        lv = make(grid=["S.o..", ".=...", "....G"], target_cell=(1, 1))
        # đứng (0,1)? dùng vị trí đứng (1,0) lăn phải: chiếm (1,1),(1,2): (1,1) cầu
        self.assertEqual(apply_move(lv, State(1, 0, O.STAND, 0), D.RIGHT).status,
                         MoveStatus.FALL_VOID)
        self.assertTrue(apply_move(lv, State(1, 0, O.STAND, 1), D.RIGHT).legal)

    def test_bridge_closing_under_block_falls(self):
        lv = Level.from_dict({
            "grid": ["S=o..", ".....", "....G"],
            "bridges": {"b1": {"cells": [[0, 1]], "open": True}},
            "switches": [{"pos": [0, 2], "type": "soft", "targets": ["b1"], "mode": "toggle"}]})
        # nằm (0,1),(0,2): đè lên công tắc soft, công tắc đóng chính cầu dưới chân -> rơi
        res = apply_move(lv, State(0, 0, O.STAND, 1), D.RIGHT)
        self.assertEqual(res.status, MoveStatus.FALL_VOID)
        self.assertTrue(res.fatal)

    def test_multiple_bridges_one_switch(self):
        lv = Level.from_dict({
            "grid": ["S.o..", "=.=..", "....G"],
            "bridges": {"b1": {"cells": [[1, 0], [1, 2]], "open": False}},
            "switches": [{"pos": [0, 2], "type": "soft", "targets": ["b1"], "mode": "open"}]})
        res = apply_move(lv, State(0, 0, O.HORIZ, 0), D.RIGHT)
        self.assertEqual(res.state.bridges, 1)

    def test_initial_state_has_bridge_bits(self):
        lv = make(init_open=True)
        self.assertEqual(initial_state(lv).bridges, 1)


if __name__ == "__main__":
    unittest.main()
