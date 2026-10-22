"""Luật chơi: nước đi hợp lệ, thắng/thua, successors, chi phí."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import List, Optional, Tuple

from .level import Level, Tile
from .state import Direction, Orient, State, TRANSITIONS


class MoveStatus(Enum):
    OK = "ok"
    WIN = "win"
    FALL_OFF_BOARD = "fall_off_board"
    FALL_VOID = "fall_void"          # rơi xuống ô trống hoặc cầu đang đóng
    FRAGILE_BREAK = "fragile_break"  # đứng lên ô dễ vỡ


@dataclass(frozen=True)
class MoveResult:
    status: MoveStatus
    state: Optional[State]  # None nếu nước đi bất hợp lệ (thua)

    @property
    def legal(self) -> bool:
        return self.status in (MoveStatus.OK, MoveStatus.WIN)


def initial_state(level: Level) -> State:
    return State(level.start[0], level.start[1], Orient.STAND, level.initial_bridges)


def is_goal(level: Level, state: State) -> bool:
    """Thắng chỉ khi khối ĐỨNG trên ô goal (nằm ngang qua goal không tính)."""
    return state.orient == Orient.STAND and (state.r, state.c) == level.goal


def _support_problem(level: Level, state: State) -> Optional[MoveStatus]:
    standing = state.orient == Orient.STAND
    cells = state.cells()
    if any(not level.in_bounds(c) for c in cells):
        return MoveStatus.FALL_OFF_BOARD
    for cell in cells:
        tile = level.tile_at(cell)
        if tile == Tile.VOID:
            return MoveStatus.FALL_VOID
        if tile == Tile.BRIDGE and not (state.bridges >> level.cell_to_bridge[cell]) & 1:
            return MoveStatus.FALL_VOID
        if tile == Tile.FRAGILE and standing:
            return MoveStatus.FRAGILE_BREAK
    return None


def _apply_switches(level: Level, previous: State, state: State) -> State:
    bridges = state.bridges
    previous_cells = set(previous.cells())
    for switch in level.switches:
        position = tuple(switch["pos"])
        if position not in state.cells() or position in previous_cells:
            continue
        switch_type = switch["type"]
        if switch_type == "heavy" and state.orient != Orient.STAND:
            continue
        if switch_type == "split":
            raise NotImplementedError("Split switches are not implemented")

        for bridge_id in switch["targets"]:
            bit = 1 << level.bridge_ids.index(bridge_id)
            mode = switch.get("mode", "toggle")
            if mode == "toggle":
                bridges ^= bit
            elif mode == "open":
                bridges |= bit
            elif mode == "close":
                bridges &= ~bit
            else:
                raise ValueError(f"Invalid switch mode: {mode!r}")
    return replace(state, bridges=bridges)


def apply_move(level: Level, state: State, direction: Direction) -> MoveResult:
    """Dùng cho GUI/chơi tay: cho biết rõ vì sao thua."""
    if state.split is not None:
        raise NotImplementedError("Chế độ split sẽ làm ở Tuần 2")
    new_orient, dr, dc = TRANSITIONS[(state.orient, direction)]
    new = replace(state, r=state.r + dr, c=state.c + dc, orient=new_orient)
    problem = _support_problem(level, new)
    if problem is not None:
        return MoveResult(problem, None)
    new = _apply_switches(level, state, new)
    return MoveResult(MoveStatus.WIN if is_goal(level, new) else MoveStatus.OK, new)


def get_successors(level: Level, state: State) -> List[Tuple[Direction, State]]:
    """Dùng cho solver: chỉ trả về các nước đi hợp lệ. Trạng thái thắng là trạng thái kết thúc."""
    if is_goal(level, state):
        return []
    out = []
    for d in Direction:
        res = apply_move(level, state, d)
        if res.legal:
            out.append((d, res.state))
    return out


def cost(level: Level, state: State, direction: Direction, next_state: State) -> float:
    """Chi phí 1 nước đi. Tạm = 1; TV3 sẽ thay bằng hàm chi phí cho UCS."""
    return 1
