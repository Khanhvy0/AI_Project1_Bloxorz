"""Công cụ phân tích và kiểm chứng màn chơi / lời giải.

LƯU Ý: đây là công cụ KIỂM CHỨNG của TV1 (dùng trong test và script thống kê),
KHÔNG phải solver nộp bài. Solver chính thức nằm ở solvers/ (TV2, TV3).
"""
from __future__ import annotations

import heapq
import itertools
from collections import deque
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from .engine import MoveStatus, apply_move, cost, get_successors, initial_state, is_goal
from .level import Level
from .state import Direction, State


@dataclass(frozen=True)
class Exploration:
    states: int                    # số state đạt tới được (BFS toàn bộ, state goal là kết thúc)
    edges: int                     # tổng số cạnh (nước đi hợp lệ) đã duyệt
    split_states: int              # số state đang ở dạng tách khối
    truncated: bool                # True nếu chạm giới hạn `limit`, các số liệu có thể thiếu
    solvable: Optional[bool]       # None = chưa biết (bị cắt giữa chừng mà chưa thấy goal)
    optimal_steps: Optional[int]   # số nước ngắn nhất (None nếu không giải được / chưa biết)
    optimal_cost: Optional[float]  # tổng chi phí nhỏ nhất theo hàm cost() hiện tại

    @property
    def avg_branching(self) -> float:
        return self.edges / self.states if self.states else 0.0


def explore(level: Level, limit: int = 300_000) -> Exploration:
    """BFS toàn bộ không gian trạng thái + Dijkstra tìm chi phí tối ưu."""
    start = initial_state(level)
    dist = {start: 0}
    queue = deque([start])
    edges = split_states = 0
    best_steps: Optional[int] = None
    truncated = False
    while queue:
        s = queue.popleft()
        if s.is_split:
            split_states += 1
        if is_goal(level, s):
            if best_steps is None:      # BFS: state goal đầu tiên được lấy ra là nông nhất
                best_steps = dist[s]
            continue
        for _, n in get_successors(level, s):
            edges += 1
            if n not in dist:
                if len(dist) >= limit:
                    truncated = True
                    continue
                dist[n] = dist[s] + 1
                queue.append(n)

    if truncated:
        # có thể đã bỏ sót đường ngắn hơn: chỉ biết chắc "giải được" nếu đã gặp goal
        return Exploration(len(dist), edges, split_states, True,
                           True if best_steps is not None else None, None, None)
    return Exploration(len(dist), edges, split_states, False, best_steps is not None,
                       best_steps, optimal_cost(level) if best_steps is not None else None)


def optimal_cost(level: Level) -> Optional[float]:
    """Chi phí nhỏ nhất tới goal theo hàm cost() (Dijkstra). None nếu không giải được."""
    start = initial_state(level)
    best = {start: 0.0}
    counter = itertools.count()
    heap = [(0.0, next(counter), start)]
    while heap:
        g, _, s = heapq.heappop(heap)
        if g > best.get(s, float("inf")):
            continue
        if is_goal(level, s):
            return g
        for d, n in get_successors(level, s):
            ng = g + cost(level, s, d, n)
            if ng < best.get(n, float("inf")):
                best[n] = ng
                heapq.heappush(heap, (ng, next(counter), n))
    return None


def replay_cost(level: Level, path: Sequence[Direction]) -> Tuple[float, State, MoveStatus]:
    """Chạy lại lời giải bằng apply_move (đúng đường GUI dùng).
    Trả về (tổng chi phí, state cuối, status cuối). Ném ValueError nếu có nước không hợp lệ
    hoặc nếu đã thắng mà còn nước đi phía sau."""
    s = initial_state(level)
    total, status = 0.0, None
    for i, d in enumerate(path):
        if status == MoveStatus.WIN:
            raise ValueError(f"Đã thắng ở nước {i} nhưng lời giải còn {len(path) - i} nước nữa")
        res = apply_move(level, s, d)
        if not res.legal:
            raise ValueError(f"Nước thứ {i + 1} ({d.name}) không hợp lệ: {res.status.value}")
        total += cost(level, s, d, res.state)
        s, status = res.state, res.status
    return total, s, status


def cost_to_go(level: Level, limit: int = 300_000):
    """Chi phí tối ưu THẬT từ mỗi state đạt tới được tới goal (Dijkstra ngược trên toàn đồ thị).
    Trả về (h_star: dict[State, float], edges: list[(s, cost, s')]) hoặc None nếu vượt `limit`.
    State không tới được goal sẽ không có mặt trong h_star."""
    start = initial_state(level)
    seen = {start}
    queue = deque([start])
    edges, rev = [], {}
    goals = []
    while queue:
        s = queue.popleft()
        if is_goal(level, s):
            goals.append(s)
        for d, n in get_successors(level, s):
            c = cost(level, s, d, n)
            edges.append((s, c, n))
            rev.setdefault(n, []).append((s, c))
            if n not in seen:
                if len(seen) >= limit:
                    return None
                seen.add(n)
                queue.append(n)
    h = {g: 0.0 for g in goals}
    counter = itertools.count()
    heap = [(0.0, next(counter), g) for g in goals]
    heapq.heapify(heap)
    while heap:
        d, _, s = heapq.heappop(heap)
        if d > h.get(s, float("inf")):
            continue
        for p, c in rev.get(s, ()):
            nd = d + c
            if nd < h.get(p, float("inf")):
                h[p] = nd
                heapq.heappush(heap, (nd, next(counter), p))
    return h, edges
