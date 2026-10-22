# Mã nguồn này không được sử dụng trực tiếp bởi nguời dùng mà chỉ dành cho thuật toán chạy ở giữa
import heapq
from collections import deque
from solvers.utils.graph import MazeGraph, StateType, STANDING





def ln_norm(sour_rc: tuple[int, int], dest_rc: tuple[int, int], n: int) -> float:
    if n <= 0:
        raise ValueError("Norm degree must be > 0")
    
    dist = sum(abs(s - d) ** n for s, d in zip(sour_rc, dest_rc)) ** (1.0 / n)
    return dist


def l1_heuristic(state: StateType, goal_rc: tuple[int, int]) -> float:
    """Khoảng cách Manhattan chia 2 + Phạt hướng nằm (Orientation-aware term)."""
    r, c, orient, _ = state
    h = ln_norm((r, c), goal_rc, 1) / 2.0
    # Nếu khối gỗ đang nằm (orient != STANDING), nó cần ít nhất 1 bước dựng đứng để lọt xuống lỗ
    if orient != STANDING and (r, c) != goal_rc:
        h += 0.5

    return h


def l2_heuristic(state: StateType, goal_rc: tuple[int, int]) -> float:
    """Khoảng cách Euclid chia 2."""
    r, c, _, _ = state

    return ln_norm((r, c), goal_rc, 2) / 2.0


heuristic_dict = {
    "l1": l1_heuristic,
    "l2": l2_heuristic,
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
    graph: MazeGraph, heuristic: str="l2"
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
    h_func = heuristic_dict[heuristic]

    # Counter phụ `tie_breaker` giúp heapq không bị lỗi khi 2 state có cùng f_score
    tie_breaker = 0
    open_set = [(h_func(start, goal_rc), 0.0, tie_breaker, start)]
    came_from: dict[StateType, tuple[StateType | None, str | None]] = {
        start: (None, None)
    }
    g_score: dict[StateType, float] = {start: 0.0}
    expanded_nodes = 0

    while open_set:
        _, current_g, _, current = heapq.heappop(open_set)

        # Bỏ qua nếu đây là bản ghi cũ trong Priority Queue có chi phí tệ hơn
        if current_g > g_score.get(current, float("inf")):
            continue

        expanded_nodes += 1

        if graph.is_goal(current):
            return reconstruct_actions(came_from, current), expanded_nodes

        for action, neighbor, step_cost in graph.get_neighbors(current):
            tentative_g = current_g + step_cost
            # Tính toán chi phí từ các đỉnh lân cận đến đích( heuristic)
            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = (current, action)
                g_score[neighbor] = tentative_g
                f_score = tentative_g + h_func(neighbor, goal_rc)
                tie_breaker += 1
                heapq.heappush(open_set, (f_score, tentative_g, tie_breaker, neighbor))
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

        expanded_nodes = 1

        if graph.is_goal(current):
            return reconstruct_actions(came_from, current), expanded_nodes
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


# TO DO( của thành viên khác)
def bfs_search(graph: MazeGraph) -> tuple[list[str], int]:
    # Gợi ý khung cho thành viên nhóm:
    # - Dùng deque([graph.start_state])
    # - Mỗi lần popleft() thì tăng expanded_nodes += 1
    # - Duyệt `for action, neighbor, _ in graph.get_neighbors(current):`
    # - Trả về `reconstruct_actions(came_from, current), expanded_nodes`
    pass


# TO DO( của thành viên khác)
def dfs_search(graph: MazeGraph) -> tuple[list[str], int]:
    # Gợi ý khung cho thành viên nhóm:
    # - Dùng stack = [graph.start_state]
    # - Trả về `reconstruct_actions(came_from, current), expanded_nodes`
    pass