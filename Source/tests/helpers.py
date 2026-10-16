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
