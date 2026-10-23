"""Hàm phụ cho test (KHÔNG phải solver chính thức): BFS tối giản để kiểm tra màn chơi giải được."""
from collections import deque
from game import get_successors, initial_state, is_goal


def bfs_path_length(level):
    start = initial_state(level)
    seen = {start}
    q = deque([(start, 0)])
    while q:
        s, d = q.popleft()
        if is_goal(level, s):
            return d
        for _, nxt in get_successors(level, s):
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, d + 1))
    return None


def bfs_path(level):
    """Trả về list Direction của lời giải ngắn nhất (hoặc None)."""
    start = initial_state(level)
    parent = {start: None}
    q = deque([start])
    while q:
        s = q.popleft()
        if is_goal(level, s):
            path = []
            while parent[s] is not None:
                s, d = parent[s]
                path.append(d)
            return path[::-1]
        for d, nxt in get_successors(level, s):
            if nxt not in parent:
                parent[nxt] = (s, d)
                q.append(nxt)
    return None


def replay(level, path):
    """Chạy lại lời giải bằng apply_move (đường đi GUI dùng). Trả về (trạng thái cuối, trạng thái, mọi sự kiện)."""
    from game import apply_move
    s, events = initial_state(level), []
    status = None
    for d in path:
        res = apply_move(level, s, d)
        assert res.legal, f"nước {d} không hợp lệ: {res.status}"
        s, status = res.state, res.status
        events += res.events
    return s, status, events

