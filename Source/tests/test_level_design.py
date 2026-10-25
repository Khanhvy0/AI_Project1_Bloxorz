"""Kiểm tra màn chuyển từ GBA và giữ các tình huống cơ chế TV2 trong fixtures."""
from dataclasses import replace
import json
from pathlib import Path
import unittest

from game import MOVES, Orient, Tile, engine, load_level
from solvers.bfs import BFSSovler
from solvers.utils.engine_graph import ACTION_TO_DIRECTION, EngineGraph
from levels.import_gba import convert


LEVELS = Path(__file__).resolve().parents[1] / "levels"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
OPTIMAL_LENGTHS = (7, 17, 22, 28, 33, 35, 44, 47, 65, 46, 67, 85, 67, 71,
                   65, 71, 129, 65, 104, 91, 114)


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
    def test_narrow_walkways_cannot_be_bypassed(self):
        for number, cell in ((3, (4, 4)), (19, (1, 4))):
            with self.subTest(level=number):
                level = load(number)
                r, c = cell
                self.assertEqual(level.tile_at(cell), Tile.FLOOR)
                # Lối một ô có khoảng trống ở hai bên và thực sự nằm trên tuyến bắt buộc.
                self.assertTrue(any(
                    all(level.tile_at(pos) == Tile.VOID for pos in pair)
                    for pair in (((r - 1, c), (r + 1, c)),
                                 ((r, c - 1), (r, c + 1)))
                ))
                self.assertIsNone(solve(level, lambda s, a, nxt, cost: cell not in nxt.cells()))

    def test_progression_and_replay(self):
        for number, length in enumerate(OPTIMAL_LENGTHS, 1):
            with self.subTest(level=number):
                level = load(number)
                self.assertEqual(level.name, f"level_{number:02}")
                self.assertFalse(any(sw.kind == Tile.SPLIT for sw in level.switch_at.values()))
                actions = solve(level)
                self.assertIsNotNone(actions)
                self.assertEqual(len(actions), length)
                self.assertLessEqual(level.rows, 10)
                self.assertLessEqual(level.cols, 15)
                states, _ = replay(level, actions)
                self.assertTrue(engine.is_goal(level, states[-1]))

    def test_gate_switches_are_essential(self):
        # Các màn khác có nút bẫy: không bắt buộc bấm mọi công tắc của game gốc.
        for number in (2, 7, 9, 11, 17, 21):
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
        for number in (4, 10, 16, 20, 21):
            level = load(number)
            with self.subTest(level=number):
                self.assertIsNone(solve(level, lambda s, a, nxt, cost: all(
                    level.tile_at(cell) != Tile.FRAGILE for cell in nxt.cells()
                )))

    def test_fragile_rule_prevents_reachable_standing_moves(self):
        for number in (4, 10, 16, 20, 21):
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
        level = load_level(str(FIXTURES / "tv2_design_07.json"))
        states, _ = replay(level, solve(level))
        poses = {s.orient for s in states if any(
            level.tile_at(cell) == Tile.FRAGILE for cell in s.cells()
        )}
        self.assertEqual(poses, {Orient.HORIZ, Orient.VERT})

    def test_heavy_switches_are_pressed_standing(self):
        for number in (2, 7, 9, 11, 17, 21):
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
        for number in (17, 19):
            level = load(number)
            states, _ = replay(level, solve(level))
            poses = {}
            for state in states:
                poses.setdefault((state.r, state.c, state.orient), set()).add(state.bridges)
            with self.subTest(level=number):
                self.assertTrue(any(len(masks) > 1 for masks in poses.values()))

    def test_second_toggle_fixture(self):
        level = load_level(str(FIXTURES / "tv2_design_15.json"))
        mask = 1 << level.bridge_ids.index("b1")
        # Nếu cấm đóng lại cầu b1, không thể đổi sang nhánh cầu đi tới goal.
        self.assertIsNone(solve(level, lambda s, a, nxt, cost: not (
            s.bridges & mask and not nxt.bridges & mask
        )))

    def test_toggle_changes_the_solution(self):
        level = load_level(str(FIXTURES / "tv2_design_13.json"))
        opened = replace(level, switch_at={
            pos: replace(sw, mode="open") for pos, sw in level.switch_at.items()
        })
        self.assertLess(len(solve(opened)), len(solve(level)))

    def test_split_and_merge_are_required(self):
        for number in (19, 20, 21):
            level = load_level(str(FIXTURES / "tv2_split" / f"level_{number:02}.json"))
            with self.subTest(level=number):
                states, events = replay(level, solve(level))
                self.assertIn("split", events)
                self.assertIn("merge", events)
                self.assertFalse(states[-1].is_split)
                self.assertIsNone(solve(level, lambda s, a, nxt, cost: not nxt.is_split))
                if number >= 20:
                    self.assertIn("switch_control", events)
                    self.assertIsNone(solve(level, lambda s, a, nxt, cost: a != "SWITCH"))


class GbaImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reference = LEVELS / "reference"
        cls.sources = json.loads((reference / "gba_levels.json").read_text())["levels"]
        cls.selection = json.loads((reference / "selection.json").read_text())

    def test_conversion_reproduces_committed_data_without_mutating_source(self):
        before = json.dumps(self.sources, sort_keys=True)
        self.assertEqual([item["level"] for item in self.selection], list(range(1, 22)))
        for item in self.selection:
            name = f'level_{item["level"]:02}'
            with self.subTest(level=name):
                converted = convert(self.sources[item["source_stage"] - 1], name,
                                    item.get("toggle_switches", ()))
                self.assertEqual(converted, json.loads((LEVELS / f"{name}.json").read_text()))
        self.assertEqual(json.dumps(self.sources, sort_keys=True), before)

    def test_unsupported_mechanics_require_explicit_exclusion_or_adaptation(self):
        for stage in (8, 9, 10, 15, 16, 20, 23, 24, 26, 28):
            with self.subTest(stage=stage), self.assertRaisesRegex(ValueError, "split"):
                convert(self.sources[stage - 1], "test")
        for stage in (17, 25, 29, 30, 31):
            with self.subTest(stage=stage), self.assertRaisesRegex(ValueError, "mixed_switch_modes"):
                convert(self.sources[stage - 1], "test")

    def test_coordinate_convention_and_initial_bridge_states(self):
        level = load(2)
        self.assertEqual(level.start, (5, 1))
        soft = level.switch_at[(3, 2)]
        self.assertEqual(soft.kind, Tile.SOFT)
        self.assertEqual(soft.mode, "toggle")
        self.assertEqual({cell for cell, bit in level.cell_to_bridge.items()
                          if soft.mask & (1 << bit)}, {(5, 4), (5, 5)})
        for item in self.selection[:18]:
            level = load(item["level"])
            source = self.sources[item["source_stage"] - 1]
            for r, row in enumerate(source["tiles"]):
                for c, tile in enumerate(row):
                    if tile in "lrkq":
                        self.assertEqual(level.is_bridge_open(engine.initial_state(level), r, c),
                                         tile in "kq")

    def test_adapted_toggles_are_essential_and_exchange_routes(self):
        for item in self.selection[18:]:
            level = load(item["level"])
            states, _ = replay(level, solve(level))
            for key in item["toggle_switches"]:
                c, r = divmod(int(key), 10)
                pos = (r, c)
                with self.subTest(level=level.name, pos=pos):
                    switch = level.switch_at[pos]
                    self.assertEqual(switch.mode, "toggle")
                    disabled = replace(level, switch_at={
                        p: sw for p, sw in level.switch_at.items() if p != pos})
                    self.assertIsNone(solve(disabled))
                    self.assertTrue(any(
                        pos in after.cells()
                        and before.bridges & ~after.bridges & switch.mask
                        and after.bridges & ~before.bridges & switch.mask
                        for before, after in zip(states, states[1:])
                    ), "Toggle phải vừa đóng nhánh cũ vừa mở nhánh mới")


if __name__ == "__main__":
    unittest.main()
