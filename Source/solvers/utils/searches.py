import heapq
from array import array
from collections import deque

from game import engine
from game.engine import (
    COST_BASE,
    COST_BRIDGE,
    COST_FRAGILE,
    MIN_STEP_COST,
    cost,
    get_successors,
    initial_state,
    is_goal,
)
from game.level import Level, Tile
from game.state import (
    ACTION_TO_DIRECTION,
    DIRECTION_TO_ACTION,
    MOVES,
    TRANSITIONS,
    Direction,
    Orient,
    State,
)

StateType = State  # alias
STANDING, HORIZONTAL = Orient.STAND, Orient.HORIZ


def _unwrap_level(level_or_graph) -> Level:
    """Trích xuất đối tượng Level nếu đầu vào là wrapper có thuộc tính .level."""
    return getattr(level_or_graph, "level", level_or_graph)


def _get_start_state(level_or_graph):
    """Lấy trạng thái khởi đầu từ Level (qua engine.initial_state) hoặc mock graph."""
    lvl = _unwrap_level(level_or_graph)
    if isinstance(lvl, Level) or hasattr(lvl, "initial_bridges"):
        return initial_state(lvl)
    if hasattr(level_or_graph, "start_state"):
        return level_or_graph.start_state
    return level_or_graph.start


def _check_is_goal(level_or_graph, state) -> bool:
    """Kiểm tra trạng thái đích qua engine.is_goal hoặc phương thức của mock graph."""
    if hasattr(level_or_graph, "is_goal") and callable(level_or_graph.is_goal):
        return level_or_graph.is_goal(state)
    return is_goal(_unwrap_level(level_or_graph), state)


def _iter_neighbors(level_or_graph, state):
    """Sinh danh sách (action_str, next_state, step_cost) từ engine.get_successors và engine.cost."""
    if hasattr(level_or_graph, "get_neighbors") and callable(level_or_graph.get_neighbors):
        return level_or_graph.get_neighbors(state)

    lvl = _unwrap_level(level_or_graph)
    out = []
    for direction, next_state in get_successors(lvl, state):
        action_str = (
            DIRECTION_TO_ACTION[direction]
            if isinstance(direction, Direction)
            else str(direction)
        )
        step_c = cost(lvl, state, direction, next_state)
        out.append((action_str, next_state, step_c))
    return out


def has_split(level_or_graph) -> bool:
    lvl = _unwrap_level(level_or_graph)
    if getattr(level_or_graph, "has_split", False):
        return True
    if hasattr(lvl, "switch_at"):
        return any(sw.kind == Tile.SPLIT for sw in lvl.switch_at.values())
    return False


def ln_norm(sour_rc: tuple[int, int], dest_rc: tuple[int, int], n: int) -> float:
    if n <= 0:
        raise ValueError("Norm degree must be > 0")
    return sum(abs(s - d) ** n for s, d in zip(sour_rc, dest_rc)) ** (1.0 / n)


def chebyshev_orientation_heuristic(state: StateType, goal_rc: tuple[int, int]) -> float:
    """Chuẩn Chebyshev (L_inf = max theo hàng và cột) kết hợp hướng của khối."""
    if getattr(state, "split", None) is not None:
        return 0.0
    r, c, orient = state.r, state.c, state.orient
    gr, gc = goal_rc
    if orient == STANDING:
        dr = abs(r - gr)
        dc = abs(c - gc)
    elif orient == HORIZONTAL:
        dr = abs(r - gr)
        dc = min(abs(c - gc), abs(c + 1 - gc))
    else:  # VERTICAL
        dr = min(abs(r - gr), abs(r + 1 - gr))
        dc = abs(c - gc)

    h_r = (2 * dr + 1) // 3
    h_c = (2 * dc + 1) // 3
    return float(max(h_r, h_c)) * MIN_STEP_COST


def l2_heuristic(state: StateType, goal_rc: tuple[int, int]) -> float:
    """Khoảng cách Euclid giữa ô neo và goal, chia 2."""
    if getattr(state, "split", None) is not None:
        return 0.0
    r, c = (state.r, state.c) if hasattr(state, "r") else (state[0], state[1])
    dr = r - goal_rc[0]
    dc = c - goal_rc[1]
    return ((dr * dr + dc * dc) ** 0.5) * 0.5 * MIN_STEP_COST


def l1_heuristic(state: StateType, goal_rc: tuple[int, int]) -> float:
    """Manhattan giữa ô neo và goal, chia 2."""
    if getattr(state, "split", None) is not None:
        return 0.0
    r, c = (state.r, state.c) if hasattr(state, "r") else (state[0], state[1])
    return (abs(r - goal_rc[0]) + abs(c - goal_rc[1])) * 0.5 * MIN_STEP_COST


def build_pose_heuristic(level_or_graph):
    """Heuristic 'pose': số bước tối thiểu trong bài toán NỚI LỎNG (mọi cầu mở, bỏ qua tác dụng công tắc)."""
    level = _unwrap_level(level_or_graph)
    R, C = level.rows, level.cols

    def get_cells(r, c, o):
        if o == Orient.STAND:
            return ((r, c),)
        elif o == Orient.HORIZ:
            return ((r, c), (r, c + 1))
        return ((r, c), (r + 1, c))

    def valid(r, c, o):
        for cr, cc in get_cells(r, c, o):
            if not (0 <= cr < R and 0 <= cc < C):
                return False
            tile = level.tiles[cr][cc]
            if tile == Tile.VOID or (tile == Tile.FRAGILE and o == Orient.STAND):
                return False
        return True

    dist = array("f", [-1.0]) * (3 * R * C)
    sources = [level.goal] + [
        pos for pos, sw in level.switch_at.items() if sw.kind == Tile.SPLIT
    ]
    q = deque()
    for r, c in sources:
        if valid(r, c, Orient.STAND):
            idx = (r * C + c) * 3 + int(Orient.STAND)
            if dist[idx] < 0.0:
                dist[idx] = 0.0
                q.append((r, c, Orient.STAND))

    while q:
        r, c, o = q.popleft()
        d = dist[(r * C + c) * 3 + int(o)]
        for move in MOVES:
            no, dr, dc = TRANSITIONS[(o, move)]
            nr, nc = r + dr, c + dc
            if valid(nr, nc, no):
                i = (nr * C + nc) * 3 + int(no)
                if dist[i] < 0.0:
                    dist[i] = d + MIN_STEP_COST
                    q.append((nr, nc, no))
                elif d + MIN_STEP_COST < dist[i]:
                    dist[i] = d + MIN_STEP_COST
    return dist, C


heuristic_dict = {
    "l1": l1_heuristic,
    "l2": l2_heuristic,
    "chebyshev": chebyshev_orientation_heuristic,
}


def make_heuristic(level_or_graph, name: str = "pose"):
    """Trả về h(state, goal_rc) cho Level."""
    if name == "pose":
        dist, C = build_pose_heuristic(level_or_graph)

        def h_pose(s, _goal):
            if getattr(s, "split", None) is not None:
                return 0.0
            d = dist[(s.r * C + s.c) * 3 + int(s.orient)]
            return float("inf") if d < 0 else float(d)

        return h_pose
    if name not in heuristic_dict:
        raise ValueError(
            f"Heuristic không tồn tại: {name!r} (chọn: pose, {', '.join(heuristic_dict)})"
        )
    if has_split(level_or_graph):
        return lambda s, _goal: 0.0
    return heuristic_dict[name]


def reconstruct_actions(
    came_from: dict[StateType, tuple[StateType | None, str | None]],
    goal_state: StateType,
) -> list[str]:
    """Truy vết ngược từ trạng thái đích về trạng thái đầu để lấy danh sách thao tác."""
    actions = []
    curr = goal_state
    while came_from[curr][0] is not None:
        prev_state, action = came_from[curr]
        actions.append(action)
        curr = prev_state
    return actions[::-1]


def a_star_search(level_or_graph, heuristic: str = "pose") -> tuple[list[str], int]:
    """Thuật toán tìm đường A*, f(n) = g(n) + h(n)."""
    lvl = _unwrap_level(level_or_graph)
    start = _get_start_state(level_or_graph)
    goal_rc = getattr(lvl, "goal", getattr(level_or_graph, "goal_pos", None))
    h_func = make_heuristic(level_or_graph, heuristic)

    start_h = h_func(start, goal_rc)
    if start_h == float("inf"):
        return [], 0

    tie_breaker = 0
    open_set = [(start_h, 0.0, tie_breaker, start)]
    came_from: dict[StateType, tuple[StateType | None, str | None]] = {
        start: (None, None)
    }
    g_score: dict[StateType, float] = {start: 0.0}
    expanded_nodes = 0

    while open_set:
        f, neg_g, _, current = heapq.heappop(open_set)
        current_g = -neg_g

        if current_g > g_score.get(current, float("inf")):
            continue

        if _check_is_goal(level_or_graph, current):
            return reconstruct_actions(came_from, current), expanded_nodes

        expanded_nodes += 1
        for action, neighbor, step_cost in _iter_neighbors(level_or_graph, current):
            tentative_g = current_g + step_cost
            if tentative_g < g_score.get(neighbor, float("inf")):
                h = h_func(neighbor, goal_rc)
                if h == float("inf"):
                    continue
                came_from[neighbor] = (current, action)
                g_score[neighbor] = tentative_g
                tie_breaker += 1
                heapq.heappush(
                    open_set, (tentative_g + h, -tentative_g, tie_breaker, neighbor)
                )
    return [], expanded_nodes


def ucs_search(level_or_graph) -> tuple[list[str], int]:
    """Thuật toán tìm đường UCS."""
    start = _get_start_state(level_or_graph)
    tie_breaker = 0
    open_set = [(0.0, tie_breaker, start)]
    came_from: dict[StateType, tuple[StateType | None, str | None]] = {
        start: (None, None)
    }
    cost_so_far: dict[StateType, float] = {start: 0.0}
    expanded_nodes = 0

    while open_set:
        current_cost, _, current = heapq.heappop(open_set)

        if current_cost > cost_so_far.get(current, float("inf")):
            continue

        if _check_is_goal(level_or_graph, current):
            return reconstruct_actions(came_from, current), expanded_nodes

        expanded_nodes += 1
        for action, neighbor, step_cost in _iter_neighbors(level_or_graph, current):
            new_cost = current_cost + step_cost

            if new_cost < cost_so_far.get(neighbor, float("inf")):
                cost_so_far[neighbor] = new_cost
                came_from[neighbor] = (current, action)
                tie_breaker += 1
                heapq.heappush(open_set, (new_cost, tie_breaker, neighbor))
    return [], expanded_nodes


def bfs_search(level_or_graph) -> tuple[list[str], int]:
    """BFS tối ưu số bước."""
    start = _get_start_state(level_or_graph)
    queue = deque([start])
    parent = {start: (None, None)}
    expanded = 0
    while queue:
        state = queue.popleft()
        if _check_is_goal(level_or_graph, state):
            return reconstruct_actions(parent, state), expanded
        expanded += 1
        for action, next_state, _ in _iter_neighbors(level_or_graph, state):
            if next_state not in parent:
                parent[next_state] = (state, action)
                queue.append(next_state)
    return [], expanded


def dfs_search(level_or_graph) -> tuple[list[str], int]:
    """DFS dùng stack, không tối ưu."""
    start = _get_start_state(level_or_graph)
    stack = [start]
    visited = {start}
    parent = {start: (None, None)}
    expanded = 0
    while stack:
        state = stack.pop()
        if _check_is_goal(level_or_graph, state):
            return reconstruct_actions(parent, state), expanded
        expanded += 1
        for action, next_state, _ in reversed(_iter_neighbors(level_or_graph, state)):
            if next_state not in visited:
                visited.add(next_state)
                parent[next_state] = (state, action)
                stack.append(next_state)
    return [], expanded


def ids_search(level_or_graph, max_depth=200) -> tuple[list[str], int]:
    """IDS Graph-Search có cờ has_cutoff."""
    if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
        raise ValueError("max_depth phải là số nguyên không âm")
    start = _get_start_state(level_or_graph)
    expanded = 0
    for limit in range(max_depth + 1):
        stack = [(start, [])]
        best_depth = {start: 0}
        has_cutoff = False
        while stack:
            state, actions = stack.pop()
            depth = len(actions)

            if depth > best_depth[state]:
                continue

            if _check_is_goal(level_or_graph, state):
                return actions, expanded
            if depth >= limit:
                has_cutoff = True
                continue
            expanded += 1
            for action, next_state, _ in reversed(_iter_neighbors(level_or_graph, state)):
                new_depth = depth + 1
                if next_state not in best_depth or new_depth < best_depth[next_state]:
                    best_depth[next_state] = new_depth
                    stack.append((next_state, actions + [action]))
        if not has_cutoff:
            break

    return [], expanded