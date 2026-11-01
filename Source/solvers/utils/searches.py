# Mã nguồn này không được sử dụng trực tiếp bởi nguời dùng mà chỉ dành cho thuật toán chạy ở giữa
import heapq
from array import array
from collections import deque

from game.engine import COST_BASE, COST_BRIDGE, COST_FRAGILE, MIN_STEP_COST
from game.level import Tile
from game.state import MOVES, TRANSITIONS, Orient, State

StateType = State # alias giữ tên cũ cho các chú thích kiểu bên dưới
STANDING, HORIZONTAL = Orient.STAND, Orient.HORIZ

def ln_norm(sour_rc: tuple[int, int], dest_rc: tuple[int, int], n: int) -> float:
    if n <= 0:
        raise ValueError("Norm degree must be > 0")
    
    dist = sum(abs(s - d) ** n for s, d in zip(sour_rc, dest_rc)) ** (1.0 / n)
    return dist


def chebyshev_orientation_heuristic(state: StateType, goal_rc: tuple[int, int]) -> float:
    """Chuẩn Chebyshev (L_inf = max theo hàng và cột) kết hợp hướng của khối.
    Tính cận dưới số bước trên từng trục từ các ô khối đang chiếm (trung bình 3 ô tốn 2 bước),
    sau đó lấy max(h_r, h_c) đúng bản chất Chebyshev. Đảm bảo 100% Admissible.
    State đang tách khối trả về 0."""
    if state.split is not None:
        return 0.0
    r, c, orient = state.r, state.c, state.orient
    gr, gc = goal_rc
    if orient == STANDING:
        dr = abs(r - gr)
        dc = abs(c - gc)
        # Khi đang ĐỨNG muốn về ĐỨNG tại goal: khoảng cách d=1 tốn ít nhất 2 bước,
        # nhưng nếu lấy (2*d + 1)//3 thì d=1 -> 1, d=2 -> 1, d=3 -> 2 (luôn <= số bước thật)
    elif orient == HORIZONTAL:
        dr = abs(r - gr)
        dc = min(abs(c - gc), abs(c + 1 - gc))
    else:  # VERTICAL
        dr = min(abs(r - gr), abs(r + 1 - gr))
        dc = abs(c - gc)

    h_r = (2 * dr + 1) // 3
    h_c = (2 * dc + 1) // 3
    # Chebyshev: lấy max giữa 2 trục thay vì cộng tổng
    return float(max(h_r, h_c)) * MIN_STEP_COST


def l2_heuristic(state: StateType, goal_rc: tuple[int, int]) -> float:
    """Khoảng cách Euclid giữa ô neo và goal, chia 2 (mỗi nước dời ô neo tối đa 2 ô).
    State đang tách khối trả về 0."""
    if state.split is not None:
        return 0.0
    dr = state.r - goal_rc[0]
    dc = state.c - goal_rc[1]
    return ((dr * dr + dc * dc) ** 0.5) * 0.5 * MIN_STEP_COST


def l1_heuristic(state: StateType, goal_rc: tuple[int, int]) -> float:
    """Manhattan giữa ô neo và goal, chia 2 (mỗi nước dời ô neo tối đa 2 ô).
    State đang tách khối trả về 0."""
    if state.split is not None:
        return 0.0
    return (abs(state.r - goal_rc[0]) + abs(state.c - goal_rc[1])) * 0.5 * MIN_STEP_COST


def build_pose_heuristic(graph):
    """Heuristic 'pose': số bước tối thiểu trong bài toán NỚI LỎNG (mọi cầu mở, bỏ qua tác dụng công tắc).

    BFS ngược trên không gian (r, c, hướng) từ các 'điểm đích': khối ĐỨNG trên goal, và khối ĐỨNG trên mỗi
    công tắc split. Coi công tắc split là điểm đích vì đứng lên nó khối bị dịch chuyển tới nơi khác
    (đường tắt), nên khoảng cách đi bộ tới goal có thể lớn hơn chi phí thật. Lấy min tới tập điểm này
    vẫn là cận dưới. Dùng luật di chuyển của engine (TRANSITIONS), không tự cài lại luật."""
    level = graph.level
    R, C = level.rows, level.cols

    # def valid(r, c, o):
    #     if o == Orient.STAND:
    #         cells = ((r, c),)
    #     elif o == Orient.HORIZ:
    #         cells = ((r, c), (r, c + 1))
    #     else:
    #         cells = ((r, c), (r + 1, c))
    #     for cr, cc in cells:
    #         if not (0 <= cr < R and 0 <= cc < C):
    #             return False
    #         tile = level.tiles[cr][cc]
    #         if tile == Tile.VOID or (tile == Tile.FRAGILE and o == Orient.STAND):
    #             return False      
    #     return True

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
                return False       # cầu coi như đang mở: BRIDGE hợp lệ
        return True

    def pose_step_cost(r, c, o) -> float:
        """Chi phí khi khối bước VÀO trạng thái (r, c, o), đồng bộ với hàm cost()."""
        has_bridge = False
        for cr, cc in get_cells(r, c, o):
            tile = level.tiles[cr][cc]
            if tile == Tile.FRAGILE:
                return COST_FRAGILE
            if tile == Tile.BRIDGE:
                has_bridge = True
        return COST_BRIDGE if has_bridge else COST_BASE

    # dist = array("i", [-1]) * (3 * R * C)
    # sources = [level.goal] + [pos for pos, sw in level.switch_at.items() if sw.kind == Tile.SPLIT]
    # q = deque()
    # for (r, c) in sources:
    #     dist[(r * C + c) * 3 + Orient.STAND] = 0.0
    #     q.append((r, c, Orient.STAND))
    # while q:
    #     r, c, o = q.popleft()
    #     d = dist[(r * C + c) * 3 + o]
    #     for move in MOVES:         # lăn là phép đảo ngược được nên mở rộng "tiến" từ đích cũng đúng
    #         no, dr, dc = TRANSITIONS[(o, move)]
    #         nr, nc = r + dr, c + dc
    #         if valid(nr, nc, no):
    #             i = (nr * C + nc) * 3 + no
    #             if dist[i] < 0:
    #                 dist[i] = d + 1
    #                 q.append((nr, nc, no))
    # return dist, C

    # Dùng mảng float ("f") khởi tạo -1.0 để lưu trực tiếp chi phí tích lũy
    dist = array("f", [-1.0]) * (3 * R * C)
    sources = [level.goal] + [pos for pos, sw in level.switch_at.items() if sw.kind == Tile.SPLIT]
    q = deque()
    for (r, c) in sources:
        idx = (r * C + c) * 3 + Orient.STAND
        dist[idx] = 0.0
        q.append((r, c, Orient.STAND))

    while q:
        r, c, o = q.popleft()
        d = dist[(r * C + c) * 3 + o]
        # Đi ngược từ (r, c, o) về (nr, nc, no) nghĩa là bước tiến vào (r, c, o)
        # Lưu ý: Để tuyệt đối không bao giờ overestimate khi dùng BFS thuần (không phải Dijkstra)
        # trên đồ thị có trọng số 1.0 / 1.5 / 2.0, bước cuối vào (r, c, o) luôn tốn đúng step_c,
        # hoặc an toàn nhất: cộng step_c cho bước đầu tiên rời khỏi (nr, nc, no)
        step_c = pose_step_cost(r, c, o)
        for move in MOVES:         # lăn là phép đảo ngược được nên mở rộng "tiến" từ đích cũng đúng
            no, dr, dc = TRANSITIONS[(o, move)]
            nr, nc = r + dr, c + dc
            if valid(nr, nc, no):
                i = (nr * C + nc) * 3 + no
                if dist[i] < 0.0:
                    # Để BFS thuần 100% admissible trên mọi cấu hình bản đồ,
                    # bước ngay sát(nr,nc,no) -> (r,c,o) lấy MIN_STEP_COST nếu đường dài,
                    # hoặc nếu muốn chặt hơn mà vẫn dùng BFS:
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


def make_heuristic(graph, name: str = "pose"):
    """Trả về h(state, goal_rc) cho graph. Mọi heuristic đều trả 0 với state đang tách khối.
    Các heuristic theo khoảng cách (l1, l2, chebyshev) KHÔNG admissible khi màn có công tắc split
    (khối bị dịch chuyển nên đường thật có thể ngắn hơn), nên màn đó dùng h = 0. 'pose' đã tính đường tắt."""
    if name == "pose":
        dist, C = build_pose_heuristic(graph)

        def h_pose(s, _goal):
            if s.split is not None:
                return 0.0
            d = dist[(s.r * C + s.c) * 3 + s.orient]
            return float("inf") if d < 0 else float(d) * MIN_STEP_COST
        return h_pose
    if name not in heuristic_dict:
        raise ValueError(f"Heuristic không tồn tại: {name!r} (chọn: pose, {', '.join(heuristic_dict)})")
    if getattr(graph, "has_split", False):
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



def a_star_search(graph, heuristic: str = "pose") -> tuple[list[str], int]:
    """Thuật toán tìm đường A*, f(n) = g(n) + h(n).

    Args:
        graph: đồ thị (EngineGraph) cung cấp start_state / is_goal / get_neighbors.
        heuristic (str): "pose" (mặc định), "l1", "l2" hoặc "chebyshev".

    Returns:
        - Danh sách thao tác từ đầu tới goal ([] nếu không có đường đi).
        - Số đỉnh đã mở rộng.
    """
    start = graph.start_state
    goal_rc = graph.goal_pos
    h_func = make_heuristic(graph, heuristic)

    # tie_breaker giúp heapq không phải so sánh State khi hai mục cùng (f, g)
    start_h = h_func(start, goal_rc)
    if start_h == float("inf"):
        return [], 0

    tie_breaker = 0
    # open_set = [(h_func(start_h, goal_rc), 0.0, tie_breaker, start)]
    open_set = [(start_h, 0.0, tie_breaker, start)]
    came_from: dict[StateType, tuple[StateType | None, str | None]] = {
        start: (None, None)
    }
    g_score: dict[StateType, float] = {start: 0.0}
    expanded_nodes = 0

    while open_set:
        f, neg_g, _, current = heapq.heappop(open_set)
        current_g = -neg_g

        # Bỏ qua bản ghi cũ trong hàng đợi có chi phí tệ hơn
        if current_g > g_score.get(current, float("inf")):
            continue

        if graph.is_goal(current):
            return reconstruct_actions(came_from, current), expanded_nodes

        expanded_nodes += 1
        for action, neighbor, step_cost in graph.get_neighbors(current):
            tentative_g = current_g + step_cost
            if tentative_g < g_score.get(neighbor, float("inf")):
                h = h_func(neighbor, goal_rc)
                if h == float("inf"):
                    continue          # state chắc chắn không tới được goal
                came_from[neighbor] = (current, action)
                g_score[neighbor] = tentative_g
                tie_breaker += 1
                heapq.heappush(open_set, (tentative_g + h, -tentative_g, tie_breaker, neighbor))
    # Không có đường đi
    return [], expanded_nodes


def ucs_search(graph) -> tuple[list[str], int]:
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
    """
    IDS Graph-Search:
    - Có cờ has_cutoff để dừng sớm nếu đồ thị đã được duyệt cạn mà không có nghiệm.
    - Dùng best_depth trong từng lần lặp để triệt tiêu chu trình.
    """
    if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
        raise ValueError("max_depth phải là số nguyên không âm")
    expanded = 0
    for limit in range(max_depth + 1):
        stack = [(graph.start_state, [])]
        best_depth = {graph.start_state: 0}
        has_cutoff = False 
        while stack:
            state, actions = stack.pop()
            depth = len(actions)
            # Bỏ qua nếu đã tìm được đường ngắn hơn tới state này
            if depth > best_depth[state]:
                continue
            # Kiểm tra Goal
            if graph.is_goal(state):
                return actions, expanded
            # Chạm trần độ sâu của vòng lặp hiện tại
            if depth >= limit:
                has_cutoff = True  # Đánh dấu còn nhánh chưa duyệt sâu hơn được
                continue
            expanded += 1
            for action, next_state, _ in reversed(graph.get_neighbors(state)):
                new_depth = depth + 1
                if next_state not in best_depth or new_depth < best_depth[next_state]:
                    best_depth[next_state] = new_depth
                    stack.append((next_state, actions + [action]))
        # Nếu duyệt hết toàn bộ không gian mà không có node nào chạm limit -> vô nghiệm hoàn toàn
        if not has_cutoff:
            break

    return [], expanded