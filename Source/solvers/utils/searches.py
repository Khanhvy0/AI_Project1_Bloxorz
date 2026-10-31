# Mã nguồn này không được sử dụng trực tiếp bởi nguời dùng mà chỉ dành cho thuật toán chạy ở giữa
import heapq
from array import array
from collections import deque
from solvers.utils.graph import MazeGraph, StateType, STANDING, HORIZONTAL

def ln_norm(sour_rc: tuple[int, int], dest_rc: tuple[int, int], n: int) -> float:
    if n <= 0:
        raise ValueError("Norm degree must be > 0")
    
    dist = sum(abs(s - d) ** n for s, d in zip(sour_rc, dest_rc)) ** (1.0 / n)
    return dist


def _pose(state):
    """Đọc cả State và tuple state của MazeGraph."""
    if hasattr(state, "r"):
        return state.r, state.c, state.orient
    return state[:3]


def chebyshev_orientation_heuristic(state: StateType, goal_rc: tuple[int, int]) -> float:
    """
    Tightly bounds Bloxorz movement by calculating independent row and column steps.
    No zip() or float powers are used, making it millions of operations faster.
    """
    r, c, orient = _pose(state)
    
    # Tìm toàn bộ vị trí hiện tại hình hộp chữ nhật đang sử dụng
    if orient == STANDING: # 0
        cells = [(r, c)]
    elif orient == HORIZONTAL: # 1
        cells = [(r, c), (r, c + 1)]
    else: # VERTICAL (2)
        cells = [(r, c), (r + 1, c)]
        
    min_h = float('inf')
    
    # tìm đường đi ngắn nhất đến với Goal
    for cr, cc in cells:
        dr = abs(cr - goal_rc[0])
        dc = abs(cc - goal_rc[1])
        
        h_r = (2 * dr + 1) // 3
        h_c = (2 * dc + 1) // 3
        
        min_h = min(min_h, h_r + h_c)
        
    return float(min_h)

def l2_heuristic(state: StateType, goal_rc: tuple[int, int]) -> float:
    """Manhattan / 2: mỗi nước dời ô neo nhiều nhất 2 ô, với cost tối thiểu 1."""
    r, c = (state.r, state.c) if hasattr(state, "r") else (state[0], state[1])
    dr = r - goal_rc[0]
    dc = c - goal_rc[1]
    return ((dr * dr + dc * dc) ** 0.5) * 0.5


def l1_heuristic(state: StateType, goal_rc: tuple[int, int]) -> float:
    """Khoảng cách Euclid chia 2."""
    r, c = (state.r, state.c) if hasattr(state, "r") else (state[0], state[1])
    return (abs(r - goal_rc[0]) + abs(c - goal_rc[1])) * 0.5


def build_pose_heuristic(graph):
    R, C = graph.rows, graph.cols
    all_open = (True,) * len(graph.bridge_ids)
    dist = array("i", [-1]) * (3 * R * C)   # 4 bytes per pose
    gr, gc = graph.goal_pos
    dist[(gr * C + gc) * 3] = 0
    q = deque([(gr, gc, STANDING)])
    while q:
        r, c, o = q.popleft()
        d = dist[(r * C + c) * 3 + o]
        for _, nr, nc, no in graph._candidates(r, c, o):
            if not graph.is_valid_state((nr, nc, no, all_open)):
                continue
            i = (nr * C + nc) * 3 + no
            if dist[i] < 0:
                dist[i] = d + 1
                q.append((nr, nc, no))
    return dist, C

heuristic_dict = {
    "l1": l1_heuristic,
    "l2": l2_heuristic,
    "chebyshev": chebyshev_orientation_heuristic
}

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



def a_star_search(
    graph: MazeGraph, heuristic: str="l1"
) -> tuple[list[str], int]:
    """Thuật toán tìm đường A*  

    Args:
        graph (dict): đồ thị của mê cung cần được giải.
        heurisitc_func (str): tên hàm heuristic được sử dụng.

    Returns:
        - Danh sách Vị trí các điểm Node tuần tự trên đường đi.
        Nếu không tồn tại đường đi thì trả về danh sách trống.
        - Số đỉnh được mở
    """
    start = graph.start_state
    goal_rc = graph.goal_pos
    if heuristic == "pose":
        dist, C = build_pose_heuristic(graph)
        def h_func(s, _goal):
            d = dist[(s[0] * C + s[1]) * 3 + s[2]]
            return float("inf") if d < 0 else float(d)
    else:
        h_func = heuristic_dict[heuristic]

    # Counter phụ `tie_breaker` giúp heapq không bị lỗi khi 2 state có cùng f_score
    tie_breaker = 0
    open_set = [(h_func(start, goal_rc), 0.0, start)]
    came_from: dict[StateType, tuple[StateType | None, str | None]] = {
        start: (None, None)
    }
    g_score: dict[StateType, float] = {start: 0.0}
    expanded_nodes = 0

    while open_set:
        f, neg_g, current = heapq.heappop(open_set)
        current_g = -neg_g

        # Bỏ qua nếu đây là bản ghi cũ trong Priority Queue có chi phí tệ hơn
        if current_g > g_score.get(current, float("inf")):
            continue

        if graph.is_goal(current):
            return reconstruct_actions(came_from, current), expanded_nodes

        expanded_nodes += 1
        for action, neighbor, step_cost in graph.get_neighbors(current):
            tentative_g = current_g + step_cost
            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = (current, action)
                g_score[neighbor] = tentative_g
                h = h_func(neighbor, goal_rc)

                if h == float("inf"):
                    continue
                f_score = tentative_g + h
                tie_breaker += 1
                heapq.heappush(open_set, (f_score, -tentative_g, neighbor))
    # Không có đường đi
    return [], expanded_nodes

def ucs_search(graph: MazeGraph) -> tuple[list[str], int]:
    """Thuật toán tìm đường UCS
    Args:
        graph dict: đồ thị của mê cung
            
    Returns:
        - Danh sách Vị trí các điểm Node tuần tự trên đường đi.
        Nếu không tồn tại đường đi thì trả về danh sách trống.
        - Số đỉnh được mở
    """

    start = graph.start_state
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

        if graph.is_goal(current):
            return reconstruct_actions(came_from, current), expanded_nodes
        expanded_nodes += 1
        # Mở rộng ra khu vực lân cận
        for action, neighbor, step_cost in graph.get_neighbors(current):
            new_cost = current_cost + step_cost

            if new_cost < cost_so_far.get(neighbor, float("inf")):
                cost_so_far[neighbor] = new_cost
                came_from[neighbor] = (current, action)
                tie_breaker += 1
                heapq.heappush(open_set, (new_cost, tie_breaker, neighbor))
    # Không tìm thấy đường nào
    return [], expanded_nodes


def bfs_search(graph) -> tuple[list[str], int]:
    """BFS tối ưu số bước. parent vừa dựng path vừa chống lặp toàn bộ state."""
    start = graph.start_state
    queue = deque([start])
    parent = {start: (None, None)}
    expanded = 0
    while queue:
        state = queue.popleft()
        if graph.is_goal(state):
            return reconstruct_actions(parent, state), expanded
        expanded += 1
        for action, next_state, _ in graph.get_neighbors(state):
            if next_state not in parent:
                parent[next_state] = (state, action)
                queue.append(next_state)
    return [], expanded


def dfs_search(graph) -> tuple[list[str], int]:
    """DFS dùng stack, không tối ưu; ưu tiên U, D, L, R theo thứ tự graph trả."""
    start = graph.start_state
    stack = [start]
    visited = {start}
    parent = {start: (None, None)}
    expanded = 0
    while stack:
        state = stack.pop()
        if graph.is_goal(state):
            return reconstruct_actions(parent, state), expanded
        expanded += 1
        for action, next_state, _ in reversed(graph.get_neighbors(state)):
            if next_state not in visited:
                visited.add(next_state)
                parent[next_state] = (state, action)
                stack.append(next_state)
    return [], expanded


def ids_search(graph, max_depth=200) -> tuple[list[str], int]:
    """IDS; [] có thể là vô nghiệm hoặc đã tới giới hạn, lớp cha phân biệt goal."""
    if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
        raise ValueError("max_depth phải là số nguyên không âm")
    expanded = 0
    for limit in range(max_depth + 1):
        stack = [(graph.start_state, [])]
        best_depth = {graph.start_state: 0}
        while stack:
            state, actions = stack.pop()
            depth = len(actions)
            if depth > best_depth[state]:
                continue
            if graph.is_goal(state):
                return actions, expanded
            if depth >= limit:
                continue
            expanded += 1
            for action, next_state, _ in reversed(graph.get_neighbors(state)):
                new_depth = depth + 1
                if next_state not in best_depth or new_depth < best_depth[next_state]:
                    best_depth[next_state] = new_depth
                    stack.append((next_state, actions + [action]))
    return [], expanded
