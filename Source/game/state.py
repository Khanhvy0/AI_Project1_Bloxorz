"""Biểu diễn trạng thái và bảng chuyển hướng của khối Bloxorz.

Quy ước toạ độ: (r, c) = (hàng, cột), gốc ở góc trên-trái, r tăng xuống dưới.
`(r, c)` của State là "ô neo" (anchor) = ô trên-trái của khối:
  STAND : chiếm {(r, c)}
  HORIZ : chiếm {(r, c), (r, c+1)}
  VERT  : chiếm {(r, c), (r+1, c)}
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, Optional, Tuple

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

    @property
    def opposite(self) -> "Direction":
        return _OPPOSITE[self]


_OPPOSITE = {Direction.UP: Direction.DOWN, Direction.DOWN: Direction.UP,
             Direction.LEFT: Direction.RIGHT, Direction.RIGHT: Direction.LEFT}

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


@dataclass(frozen=True)
class State:
    """Trạng thái bất biến, hashable -> dùng trực tiếp trong set/dict của solver.

    r, c, orient : vị trí ô neo và hướng của khối
    bridges      : bitmask, bit i = 1 nếu cầu thứ i đang MỞ
    split, active: dành sẵn cho split switch (Tuần 2). Hiện luôn là None / 0.
                   split = (cell_khối_A, cell_khối_B), active = khối đang điều khiển.
    """
    r: int
    c: int
    orient: Orient
    bridges: int = 0
    split: Optional[Tuple[Cell, Cell]] = None
    active: int = 0

    def cells(self) -> Tuple[Cell, ...]:
        if self.orient == Orient.STAND:
            return ((self.r, self.c),)
        if self.orient == Orient.HORIZ:
            return ((self.r, self.c), (self.r, self.c + 1))
        return ((self.r, self.c), (self.r + 1, self.c))
