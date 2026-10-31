"""Luật chơi: nước đi hợp lệ, công tắc, tách/ghép khối, thắng/thua, successors, chi phí."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from .level import Level, SwitchInfo, Tile
from .state import Cell, DELTA, Direction, MOVES, Orient, State, TRANSITIONS

CUBE_BREAKS_FRAGILE = False

class MoveStatus(Enum):
    OK = "ok"
    WIN = "win"
    FALL_OFF_BOARD = "fall_off_board"
    FALL_VOID = "fall_void"          # rơi xuống ô trống hoặc cầu đang đóng
    FRAGILE_BREAK = "fragile_break"  # đứng lên ô dễ vỡ
    BLOCKED = "blocked"              # nước đi không thực hiện được nhưng KHÔNG thua


@dataclass(frozen=True)
class MoveResult:
    status: MoveStatus
    state: Optional[State]  # None nếu nước đi không hợp lệ 
    events: Tuple[str, ...] = () # gợi ý cho GUI: "switch", "split", "merge", "switch_control"
    
    @property
    def legal(self) -> bool:
        return self.status in (MoveStatus.OK, MoveStatus.WIN)

    @property
    def fatal(self) -> bool:
        """True nếu nước đi làm THUA (GUI hiển thị thua). BLOCKED thì chỉ bỏ qua nước đi."""
        return self.status in (MoveStatus.FALL_OFF_BOARD, MoveStatus.FALL_VOID, MoveStatus.FRAGILE_BREAK)


def initial_state(level: Level) -> State:
    return State(level.start[0], level.start[1], Orient.STAND, level.initial_bridges)


def is_goal(level: Level, state: State) -> bool:
    """Thắng chỉ khi khối 1x1x2 ĐỨNG trên ô goal. Nằm ngang qua goal hoặc khối nhỏ thì không tính."""
    return (state.split is None and state.orient == Orient.STAND
                and (state.r, state.c) == level.goal)


# Kiểm tra cầu

def _bridge_open(level: Level, cell: Cell, bridges: int) -> bool:
    return bool((bridges >> level.cell_to_bridge[cell]) & 1)


def _support_problem(level: Level, cells: Tuple[Cell, ...], bridges: int, breaks_fragile: bool) -> Optional[MoveStatus]:
    if any(not level.in_bounds(c) for c in cells):
        return MoveStatus.FALL_OFF_BOARD
    for cell in cells:
        tile = level.tile_at(cell)
        if tile == Tile.VOID:
            return MoveStatus.FALL_VOID
        if tile == Tile.BRIDGE and not _bridge_open(level, cell, bridges):
            return MoveStatus.FALL_VOID
        if tile == Tile.FRAGILE and breaks_fragile:
            return MoveStatus.FRAGILE_BREAK
    return None


def _closed_bridge_under(level: Level, cells: Tuple[Cell, ...], bridges: int) -> bool:
    return any(level.tile_at(c) == Tile.BRIDGE and not _bridge_open(level, c, bridges) for c in cells)


# Kiểm tra công tắc
def _apply_mask(bridges: int, sw: SwitchInfo) -> int:
    if sw.mode == "toggle":
        return bridges ^ sw.mask
    if sw.mode == "open":
        return bridges | sw.mask
    return bridges & ~sw.mask  # "close"


def _press(level: Level, cells: Tuple[Cell, ...], bridges: int, full_block_standing: bool, events: List[str]) -> Tuple[int, Optional[SwitchInfo]]:
    """Kích hoạt các công tắc dưới `cells`.
    - soft : mọi phần của khối / khối nhỏ đều kích hoạt
    - heavy, split : chỉ khi khối 1x1x2 ĐỨNG (khối nhỏ không kích hoạt được)
    Trả về (bridges mới, công tắc split nếu có)."""
    split_sw = None
    for cell in cells:
        sw = level.switch_at.get(cell)
        if sw is None:
            continue
        if sw.kind == Tile.SOFT or (full_block_standing and sw.kind == Tile.HEAVY):
            bridges = _apply_mask(bridges, sw)
            events.append("switch")
        elif full_block_standing and sw.kind == Tile.SPLIT:
            split_sw = sw
    return bridges, split_sw

# Kiểm tra nước đi
def _move_block(level: Level, state: State, direction: Direction) -> MoveResult:
    new_orient, dr, dc = TRANSITIONS[(state.orient, direction)]
    new = state._replace(r=state.r + dr, c=state.c + dc, orient=new_orient)
    cells = new.cells()
    problem = _support_problem(level, cells, new.bridges, new_orient == Orient.STAND)
    if problem is not None:
        return MoveResult(problem, None)

    events: List[str] = []
    bridges, split_sw = _press(level, cells, new.bridges, new_orient == Orient.STAND, events)

    if split_sw is not None: # đứng trên công tắc split -> dịch chuyển + tách
        a, b = split_sw.cubes
        events.append("split")
        if _closed_bridge_under(level, (a, b), bridges):
            return MoveResult(MoveStatus.FALL_VOID, None)
        return MoveResult(MoveStatus.OK, State.make_split(a, b, a, bridges), tuple(events))

    if bridges != new.bridges:
        if _closed_bridge_under(level, cells, bridges):
            return MoveResult(MoveStatus.FALL_VOID, None)  # cầu đóng ngay dưới khối
        new = new._replace(bridges=bridges)
    status = MoveStatus.WIN if is_goal(level, new) else MoveStatus.OK
    return MoveResult(status, new, tuple(events))


def _move_cube(level: Level, state: State, direction: Direction) -> MoveResult:
    cells = list(state.split)
    cur, other = cells[state.active], cells[1 - state.active]
    dr, dc = DELTA[direction]
    nxt = (cur[0] + dr, cur[1] + dc)
    if nxt == other:
        return MoveResult(MoveStatus.BLOCKED, None)
    problem = _support_problem(level, (nxt,), state.bridges, CUBE_BREAKS_FRAGILE)
    if problem is not None:
        return MoveResult(problem, None)

    events: List[str] = []
    bridges, _ = _press(level, (nxt,), state.bridges, False, events) # khối nhỏ: chỉ soft
    if bridges != state.bridges and _closed_bridge_under(level, (nxt, other), bridges):
        return MoveResult(MoveStatus.FALL_VOID, None)

    if abs(nxt[0] - other[0]) + abs(nxt[1] - other[1]) == 1: # kề nhau -> ghép lại
        a, b = (nxt, other) if nxt < other else (other, nxt)
        orient = Orient.HORIZ if a[0] == b[0] else Orient.VERT
        events.append("merge")
        return MoveResult(MoveStatus.OK, State(a[0], a[1], orient, bridges), tuple(events))
    return MoveResult(MoveStatus.OK, State.make_split(nxt, other, nxt, bridges), tuple(events))


def apply_move(level: Level, state: State, direction: Direction) -> MoveResult:
    """Dùng cho GUI/chơi tay: cho biết rõ kết quả, lý do thua và các sự kiện."""
    if direction == Direction.SWITCH:
        if state.split is None:
            return MoveResult(MoveStatus.BLOCKED, None)
        return MoveResult(MoveStatus.OK, state._replace(active=1 - state.active), ("switch_control",))
    if state.split is not None:
        return _move_cube(level, state, direction)
    return _move_block(level, state, direction)
    

def get_successors(level: Level, state: State) -> List[Tuple[Direction, State]]:
    """Dùng cho solver: chỉ trả về các nước đi hợp lệ. Trạng thái thắng là trạng thái kết thúc.
    Khi đang tách khối, ngoài 4 hướng còn có Direction.SWITCH (đổi khối điều khiển)."""
    if is_goal(level, state):
        return []
    dirs = MOVES + (Direction.SWITCH,) if state.split is not None else MOVES
    out = []
    for d in dirs:
        res = apply_move(level, state, d)
        if res.legal:
            out.append((d, res.state))
    return out


def cost(level: Level, state: State, direction: Direction, next_state: State) -> float:
    """Hàm chi phí UCS được thiết kế không đồng nhất nhằm phản ánh tính chất vật lý và mức độ rủi ro."""
    
    # Thao tác chuyển đổi quyền điều khiển (lúc khối bị tách) tính là hành động bình thường
    if direction == Direction.SWITCH:
        return 1.0

    # Trạng thái trước đó nguyên khối nhưng trạng thái tiếp theo bị tách (split),
    # hành động a vừa kích hoạt công tắc chia tách (Split Switch)
    if state.split is None and next_state.split is not None:
        return 0.5

    # Xác định các ô (cells) ở trạng thái s'
    if next_state.split is not None:
        cells = next_state.split
    else:
        cells = next_state.cells()

    # Công tắc nặng
    is_standing = (next_state.orient == Orient.STAND and next_state.split is None)
    is_switch_activated = False

    # Duyệt qua các ô ở trạng thái s'
    for cell in cells:
        tile = level.tile_at(cell)
        
        # s' chiếm giữ ô dễ vỡ (Fragile)
        if tile == Tile.FRAGILE:
            return 2.0
            
        # kích hoạt công tắc (Switch mềm hoặc Switch nặng)
        if tile == Tile.SOFT or (tile == Tile.HEAVY and is_standing):
            is_switch_activated = True

    # bất kỳ công tắc nào được kích hoạt
    if is_switch_activated:
        return 0.5
        
    # Trả về 1.0 trong các trường hợp di chuyển bình thường còn lại
    return 1.0