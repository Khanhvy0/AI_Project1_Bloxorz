"""Biểu diễn trạng thái và bảng chuyển hướng của khối Bloxorz.

Quy ước toạ độ: (r, c) = (hàng, cột), gốc ở góc trên-trái, r tăng xuống dưới.
`(r, c)` của State là "ô neo" (anchor) = ô trên-trái của khối:
  STAND : chiếm {(r, c)}
  HORIZ : chiếm {(r, c), (r, c+1)}
  VERT  : chiếm {(r, c), (r+1, c)}
"""
from __future__ import annotations

from enum import IntEnum
from typing import Dict, Optional, Tuple, NamedTuple

Cell = Tuple[int, int]


class Orient(IntEnum):
    STAND = 0   # đứng
    HORIZ = 1   # nằm ngang
    VERT = 2    # nằm dọc


class Direction(IntEnum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    SWITCH = 4  # đổi khối đang điều khiển (phím cách) - chỉ hợp lệ khi đang tách khối

    @property
    def opposite(self) -> "Direction":
        return _OPPOSITE[self]


_OPPOSITE = {Direction.UP: Direction.DOWN, Direction.DOWN: Direction.UP, Direction.LEFT: Direction.RIGHT, Direction.RIGHT: Direction.LEFT, Direction.SWITCH: Direction.SWITCH}

# 4 hướng lăn (không gồm SWITCH)
MOVES = (Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT)
DELTA = {Direction.UP: (-1, 0), Direction.DOWN: (1, 0), Direction.LEFT: (0, -1), Direction.RIGHT: (0, 1)}

# (hướng hiện tại, hướng lăn) -> (hướng mới, dr, dc) ; (dr, dc) là độ dời của ô neo
TRANSITIONS: Dict[Tuple[Orient, Direction], Tuple[Orient, int, int]] = {
    # Đang đứng: ngã xuống nằm theo hướng lăn
    (Orient.STAND, Direction.UP):    (Orient.VERT,  -2,  0),
    (Orient.STAND, Direction.DOWN):  (Orient.VERT,   1,  0),
    (Orient.STAND, Direction.LEFT):  (Orient.HORIZ,  0, -2),
    (Orient.STAND, Direction.RIGHT): (Orient.HORIZ,  0,  1),
    # Đang nằm ngang: lăn trái/phải -> đứng dậy; lăn lên/xuống -> vẫn nằm ngang
    (Orient.HORIZ, Direction.LEFT):  (Orient.STAND,  0, -1),
    (Orient.HORIZ, Direction.RIGHT): (Orient.STAND,  0,  2),
    (Orient.HORIZ, Direction.UP):    (Orient.HORIZ, -1,  0),
    (Orient.HORIZ, Direction.DOWN):  (Orient.HORIZ,  1,  0),
    # Đang nằm dọc: lăn lên/xuống -> đứng dậy; lăn trái/phải -> vẫn nằm dọc
    (Orient.VERT, Direction.UP):     (Orient.STAND, -1,  0),
    (Orient.VERT, Direction.DOWN):   (Orient.STAND,  2,  0),
    (Orient.VERT, Direction.LEFT):   (Orient.VERT,   0, -1),
    (Orient.VERT, Direction.RIGHT):  (Orient.VERT,   0,  1),
}

DIRECTION_TO_ACTION: Dict[Direction, str] = {
    Direction.UP: "U",
    Direction.DOWN: "D",
    Direction.LEFT: "L",
    Direction.RIGHT: "R",
}

if hasattr(Direction, "SWITCH"):
    DIRECTION_TO_ACTION[getattr(Direction, "SWITCH")] = "S"

ACTION_TO_DIRECTION: Dict[str, Direction] = {
    v: k for k, v in DIRECTION_TO_ACTION.items()
}


class State(NamedTuple):
    """Trạng thái bất biến, hashable (NamedTuple: hash/so sánh chạy ở mức C, nhanh hơn dataclass).

    Chế độ khối thường (split is None):
        r, c, orient : ô neo và hướng của khối
    Chế độ tách khối (split is not None):
        split  = (cell_nhỏ, cell_lớn) hai khối lập phương, đã sắp xếp để trạng thái là DUY NHẤT
        active = chỉ số (0/1) của khối đang điều khiển trong `split`
        r, c, orient luôn là (-1, -1, STAND) để không sinh trạng thái trùng.
    bridges : bitmask, bit i = 1 nếu cầu thứ i đang MỞ (cả hai chế độ).
    """
    r: int
    c: int
    orient: Orient
    bridges: int = 0
    split: Optional[Tuple[Cell, Cell]] = None
    active: int = 0

    @property
    def is_split(self) -> bool:
        return self.split is not None

    def cells(self) -> Tuple[Cell, ...]:
        """Các ô đang bị chiếm (1 ô: đứng; 2 ô: nằm hoặc hai khối lập phương)."""
        if self.split is not None:
            return self.split
        if self.orient == Orient.STAND:
            return ((self.r, self.c),)
        if self.orient == Orient.HORIZ:
            return ((self.r, self.c), (self.r, self.c + 1))
        return ((self.r, self.c), (self.r + 1, self.c))

    @staticmethod
    def make_split(cell_a: Cell, cell_b: Cell, active_cell: Cell, bridges: int) -> "State":
        """Tạo trạng thái tách khối ở dạng chuẩn (sắp xếp 2 ô, tính chỉ số khối active)."""
        a, b = (cell_a, cell_b) if cell_a < cell_b else (cell_b, cell_a)
        return State(-1, -1, Orient.STAND, bridges, (a, b), 0 if active_cell == a else 1)

    @property
    def active_cell(self) -> Optional[Cell]:
        return None if self.split is None else self.split[self.active]