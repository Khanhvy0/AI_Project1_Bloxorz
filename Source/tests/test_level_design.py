"""Kiểm tra ý đồ màn chơi: cơ chế phải cần thiết, không chỉ có lời giải."""
from dataclasses import replace
from pathlib import Path
import unittest

from game import MOVES, Orient, Tile, engine, load_level
from solvers.bfs import BFSSovler
from solvers.utils.engine_graph import ACTION_TO_DIRECTION, EngineGraph


LEVELS = Path(__file__).resolve().parents[1] / "levels"
BANDS = (
    (4, 4), (6, 10), (8, 14), (12, 18), (8, 12), (10, 16), (14, 22),
    (8, 14), (12, 18), (16, 24), (10, 16), (16, 24), (14, 22), (18, 28),
    (20, 30), (18, 28), (22, 32), (26, 40), (10, 18), (16, 26), (22, 36),
)


def load(number):
    return load_level(str(LEVELS / f"level_{number:02}.json"))


def solve(level, allow=None):
    graph = EngineGraph(level)
    if allow is not None:
        neighbors = graph.get_neighbors
        graph.get_neighbors = lambda state: [
            edge for edge in neighbors(state) if allow(state, *edge)
        ]
    return BFSSovler(graph).run_search()[0]


def replay(level, actions):
    state = engine.initial_state(level)
    states, events = [state], []
    for action in actions:
        move = engine.apply_move(level, state, ACTION_TO_DIRECTION[action])
        assert move.legal, (action, move.status)
        state = move.state
        states.append(state)
        events.extend(move.events)
    return states, events


def reachable(level):
    start = engine.initial_state(level)
    seen, stack = {start}, [start]
    while stack:
        state = stack.pop()
        yield state
        for _, nxt in engine.get_successors(level, state):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)


class LevelDesignTests(unittest.TestCase):
    def test_progression_and_replay(self):
        for number, (low, high) in enumerate(BANDS, 1):
            with self.subTest(level=number):
                level = load(number)
                self.assertEqual(level.name, f"level_{number:02}")
                actions = solve(level)
                self.assertIsNotNone(actions)
                self.assertTrue(low <= len(actions) <= high, len(actions))
                self.assertLessEqual(level.rows, 10)
                self.assertLessEqual(level.cols, 15)
                states, _ = replay(level, actions)
                self.assertTrue(engine.is_goal(level, states[-1]))

    def test_each_switch_is_essential(self):
        for number in range(8, 22):
            level = load(number)
            self.assertTrue(level.switch_at)
            for pos in level.switch_at:
                with self.subTest(level=number, switch=pos):
                    # Chỉ vô hiệu hóa hiệu ứng; giữ nguyên ô và trạng thái cầu ban đầu.
                    disabled = replace(level, switch_at={
                        cell: sw for cell, sw in level.switch_at.items() if cell != pos
                    })
                    self.assertIsNone(solve(disabled))

    def test_fragile_cannot_be_bypassed(self):
        for number in (5, 6, 7, 16, 18, 21):
            level = load(number)
            with self.subTest(level=number):
                self.assertIsNone(solve(level, lambda s, a, nxt, cost: all(
                    level.tile_at(cell) != Tile.FRAGILE for cell in nxt.cells()
                )))

    def test_fragile_rule_prevents_reachable_standing_moves(self):
        for number in (5, 6, 7, 16, 18, 21):
            level = load(number)
            floor = replace(level, tiles=tuple(
                tuple(Tile.FLOOR if tile == Tile.FRAGILE else tile for tile in row)
                for row in level.tiles
            ))
            with self.subTest(level=number):
                witnesses = []
                for state in reachable(level):
                    for direction in MOVES:
                        move = engine.apply_move(floor, state, direction)
                        if (move.legal and not move.state.is_split
                                and move.state.orient == Orient.STAND
                                and level.tile_at(move.state.cells()[0]) == Tile.FRAGILE):
                            witnesses.append((state, direction))
                self.assertTrue(witnesses, "Fragile không hạn chế được tư thế nào")
                for state, direction in witnesses:
                    self.assertEqual(engine.apply_move(level, state, direction).status,
                                     engine.MoveStatus.FRAGILE_BREAK)

    def test_two_fragile_sections_require_different_orientations(self):
        level = load(7)
        states, _ = replay(level, solve(level))
        poses = {s.orient for s in states if any(
            level.tile_at(cell) == Tile.FRAGILE for cell in s.cells()
        )}
        self.assertEqual(poses, {Orient.HORIZ, Orient.VERT})

    def test_heavy_switches_are_pressed_standing(self):
        for number in (11, 12, 16, 17, 18, 21):
            level = load(number)
            states, _ = replay(level, solve(level))
            heavy = {pos for pos, sw in level.switch_at.items() if sw.kind == Tile.HEAVY}
            self.assertTrue(heavy)
            with self.subTest(level=number):
                for pos in heavy:
                    self.assertTrue(any(
                        before.bridges != after.bridges and not after.is_split
                        and after.orient == Orient.STAND and (after.r, after.c) == pos
                        for before, after in zip(states, states[1:])
                    ))

    def test_hub_requires_return_with_changed_bridges(self):
        for number in (14, 15, 17):
            level = load(number)
            states, _ = replay(level, solve(level))
            poses = {}
            for state in states:
                poses.setdefault((state.r, state.c, state.orient), set()).add(state.bridges)
            with self.subTest(level=number):
                self.assertTrue(any(len(masks) > 1 for masks in poses.values()))

    def test_level_15_requires_second_toggle(self):
        level = load(15)
        mask = 1 << level.bridge_ids.index("b1")
        # Nếu cấm đóng lại cầu b1, không thể đổi sang nhánh cầu đi tới goal.
        self.assertIsNone(solve(level, lambda s, a, nxt, cost: not (
            s.bridges & mask and not nxt.bridges & mask
        )))

    def test_toggle_changes_the_solution_in_level_13(self):
        level = load(13)
        opened = replace(level, switch_at={
            pos: replace(sw, mode="open") for pos, sw in level.switch_at.items()
        })
        self.assertLess(len(solve(opened)), len(solve(level)))

    def test_split_and_merge_are_required(self):
        for number in (19, 20, 21):
            level = load(number)
            with self.subTest(level=number):
                states, events = replay(level, solve(level))
                self.assertIn("split", events)
                self.assertIn("merge", events)
                self.assertFalse(states[-1].is_split)
                self.assertIsNone(solve(level, lambda s, a, nxt, cost: not nxt.is_split))
                if number >= 20:
                    self.assertIn("switch_control", events)
                    self.assertIsNone(solve(level, lambda s, a, nxt, cost: a != "SWITCH"))


if __name__ == "__main__":
    unittest.main()
