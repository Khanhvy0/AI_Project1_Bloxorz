"""Định nghĩa màn chơi và bộ nạp file JSON."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Tuple

from .state import Cell


class LevelError(ValueError):
    """File màn chơi sai định dạng."""


class Tile(IntEnum):
    VOID = 0
    FLOOR = 1
    GOAL = 2
    FRAGILE = 3
    BRIDGE = 4
    SOFT = 5     # công tắc mềm
    HEAVY = 6    # công tắc nặng
    SPLIT = 7    # công tắc tách khối


CHAR_TO_TILE = {"#": Tile.VOID, ".": Tile.FLOOR, "S": Tile.FLOOR, "G": Tile.GOAL,
                "F": Tile.FRAGILE, "=": Tile.BRIDGE, "o": Tile.SOFT,
                "x": Tile.HEAVY, "s": Tile.SPLIT}
SWITCH_TYPE_TO_TILE = {"soft": Tile.SOFT, "heavy": Tile.HEAVY, "split": Tile.SPLIT}


@dataclass
class Level:
    name: str
    tiles: Tuple[Tuple[Tile, ...], ...]
    start: Cell
    goal: Cell
    bridge_ids: List[str] = field(default_factory=list)          # chỉ số bit = vị trí trong list
    cell_to_bridge: Dict[Cell, int] = field(default_factory=dict)  # ô cầu -> chỉ số bit
    initial_bridges: int = 0
    switches: List[dict] = field(default_factory=list)           # Tuần 2 sẽ dùng

    @property
    def rows(self) -> int:
        return len(self.tiles)

    @property
    def cols(self) -> int:
        return len(self.tiles[0])

    def in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell[0] < self.rows and 0 <= cell[1] < self.cols

    def tile_at(self, cell: Cell) -> Tile:
        return self.tiles[cell[0]][cell[1]]

    @staticmethod
    def from_dict(d: dict) -> "Level":
        grid = d.get("grid")
        if not grid or not all(isinstance(row, str) for row in grid):
            raise LevelError("'grid' phải là danh sách các chuỗi")
        if len({len(row) for row in grid}) != 1:
            raise LevelError("Các hàng của 'grid' phải cùng độ dài")

        tiles, start, goal = [], None, None
        for r, row in enumerate(grid):
            line = []
            for c, ch in enumerate(row):
                if ch not in CHAR_TO_TILE:
                    raise LevelError(f"Ký tự không hợp lệ {ch!r} tại ({r},{c})")
                if ch == "S":
                    if start is not None:
                        raise LevelError("Có nhiều hơn một ô 'S'")
                    start = (r, c)
                if ch == "G":
                    if goal is not None:
                        raise LevelError("Có nhiều hơn một ô 'G'")
                    goal = (r, c)
                line.append(CHAR_TO_TILE[ch])
            tiles.append(tuple(line))
        if start is None or goal is None:
            raise LevelError("Thiếu ô 'S' (xuất phát) hoặc 'G' (đích)")

        level = Level(d.get("name", "unnamed"), tuple(tiles), start, goal)

        # Cầu: {"b1": {"cells": [[r,c],...], "open": false}}
        for idx, (bid, info) in enumerate(d.get("bridges", {}).items()):
            level.bridge_ids.append(bid)
            if info.get("open", False):
                level.initial_bridges |= 1 << idx
            for rc in info["cells"]:
                cell = (rc[0], rc[1])
                if not level.in_bounds(cell) or level.tile_at(cell) != Tile.BRIDGE:
                    raise LevelError(f"Cầu {bid}: ô {cell} không phải '=' trong grid")
                if cell in level.cell_to_bridge:
                    raise LevelError(f"Ô {cell} thuộc nhiều hơn một cầu")
                level.cell_to_bridge[cell] = idx
        for r, row in enumerate(level.tiles):
            for c, t in enumerate(row):
                if t == Tile.BRIDGE and (r, c) not in level.cell_to_bridge:
                    raise LevelError(f"Ô '=' tại ({r},{c}) chưa thuộc cầu nào")

        # Công tắc: kiểm tra vị trí khớp loại ô; logic kích hoạt làm ở Tuần 2
        for sw in d.get("switches", []):
            pos = (sw["pos"][0], sw["pos"][1])
            stype = sw.get("type")
            if stype not in SWITCH_TYPE_TO_TILE:
                raise LevelError(f"Loại công tắc không hợp lệ: {stype!r}")
            if not level.in_bounds(pos) or level.tile_at(pos) != SWITCH_TYPE_TO_TILE[stype]:
                raise LevelError(f"Công tắc {stype} tại {pos} không khớp ký tự trong grid")
            for t in sw.get("targets", []):
                if t not in level.bridge_ids:
                    raise LevelError(f"Công tắc tại {pos} trỏ tới cầu không tồn tại: {t}")
            level.switches.append(sw)
        return level


def load_level(path: str) -> Level:
    with open(path, encoding="utf-8") as f:
        return Level.from_dict(json.load(f))
