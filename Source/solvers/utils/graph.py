import json

# Quy ước theo Mục 2.2 của đề bài:
# 0: Standing tại (r, c)
# 1: Lying horizontally tại (r, c) và (r, c + 1)
# 2: Lying vertically tại (r, c) và (r + 1, c)
STANDING = 0
HORIZONTAL = 1
VERTICAL = 2

# State gồm: (r, c, orientation, bridges_status)
StateType = tuple[int, int, int, tuple[bool, ...]]


class MazeGraph:
    def __init__(self, level_data: dict):
        """
        Đọc cấu trúc JSON:
        - "grid": list[str]
        - "bridges": dict[str, {"cells": list[list[int]], "open": bool}]
        - "switches": list[{"pos": [r, c], "type": "soft"|"heavy", "targets": list[str], "mode": str}]
        """
        self.name = level_data.get("name", "unknown_level")
        self.matrix: list[str] = level_data["grid"]
        self.rows = len(self.matrix)
        self.cols = len(self.matrix[0]) if self.rows > 0 else 0
        self._open_cache: dict[tuple[bool, ...], set] = {}
        # 1. Quét ma trận "grid" để tự động tìm tọa độ Start ('S') và Goal ('G')
        start_pos = None
        goal_pos = None
        for r in range(self.rows):
            for c in range(self.cols):
                ch = self.matrix[r][c]
                if ch == "S":
                    start_pos = (r, c)
                elif ch == "G":
                    goal_pos = (r, c)

        if start_pos is None or goal_pos is None:
            raise ValueError(f"Màn chơi '{self.name}' thiếu ký tự 'S' hoặc 'G' trên grid!")

        self.goal_pos: tuple[int, int] = goal_pos

        # 2. Chuẩn hóa "bridges" từ dict sang danh sách cố định theo thứ tự tên cầu ('b1', 'b2', ...)
        raw_bridges: dict = level_data.get("bridges", {})
        self.bridge_ids: list[str] = sorted(raw_bridges.keys())
        self.bridge_id_to_idx: dict[str, int] = {
            b_id: idx for idx, b_id in enumerate(self.bridge_ids)
        }

        # Lưu danh sách các ô (r, c) của từng cây cầu và trạng thái đóng/mở ban đầu
        self.bridge_cells: list[set[tuple[int, int]]] = []
        init_bridge_states: list[bool] = []

        for b_id in self.bridge_ids:
            b_info = raw_bridges[b_id]
            cells_set = {tuple(cell) for cell in b_info.get("cells", [])}
            self.bridge_cells.append(cells_set)
            init_bridge_states.append(bool(b_info.get("open", False)))

        # Thiết lập trạng thái khởi đầu (Start State)
        self.start_state: StateType = (
            start_pos[0],
            start_pos[1],
            STANDING,
            tuple(init_bridge_states),
        )

        # 3. Chuẩn hóa "switches" từ list sang dict {(r, c): list_các_switch_tại_ô_đó}
        # để tra cứu O(1) mỗi khi khối gỗ lăn tới
        self.switches: dict[tuple[int, int], list[dict]] = {}
        for sw in level_data.get("switches", []):
            pos = tuple(sw["pos"])
            target_indices = [
                self.bridge_id_to_idx[t_id]
                for t_id in sw.get("targets", [])
                if t_id in self.bridge_id_to_idx
            ]
            sw_parsed = {
                "type": sw["type"].lower(),       # "soft" hoặc "heavy"
                "mode": sw["mode"].lower(),       # "open", "close", "toggle", "permanent"
                "target_indices": target_indices, # Danh sách index của cầu trong bridge_states
            }
            self.switches.setdefault(pos, []).append(sw_parsed)

    def _open_cells(self, bridge_states):
        s = self._open_cache.get(bridge_states)
        if s is None:
            s = set()
            for idx, is_open in enumerate(bridge_states):
                if is_open:
                    s.update(self.bridge_cells[idx])
            self._open_cache[bridge_states] = s
        return s

    @classmethod
    def from_json_file(cls, filepath: str) -> "MazeGraph":
        """Hàm tiện ích giúp tạo nhanh MazeGraph từ đường dẫn file .json."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data)

    def get_occupied_cells(self, r: int, c: int, orient: int) -> list[tuple[int, int]]:
        """Trả về danh sách các ô (r, c) mà khối gỗ đang đè lên."""
        if orient == STANDING:
            return [(r, c)]
        elif orient == HORIZONTAL:
            return [(r, c), (r, c + 1)]
        elif orient == VERTICAL:
            return [(r, c), (r + 1, c)]
        return []

    def is_valid_state(self, state: StateType) -> bool:
        """Kiểm tra khối gỗ có nằm hoàn toàn trên các ô hợp lệ hay không."""
        r, c, orient, bridge_states = state
        cells = self.get_occupied_cells(r, c, orient)

        # Tập hợp tất cả các tọa độ (r, c) của những cây cầu đang MỞ (open == True)
        open_bridge_cells: set[tuple[int, int]] = set()
        for idx, is_open in enumerate(bridge_states):
            if is_open:
                open_bridge_cells.update(self.bridge_cells[idx])

        for cell_r, cell_c in cells:
            # 1. Kiểm tra tràn biên
            if not (0 <= cell_r < self.rows and 0 <= cell_c < self.cols):
                return False

            tile = self.matrix[cell_r][cell_c]

            # 2. Kiểm tra rơi xuống vực ('#')
            if tile == "#":
                return False

            # 3. Kiểm tra ô cầu ('=' hoặc nằm trong danh sách bridge): chỉ đi được nếu cầu đang mở
            if tile == "=" and (cell_r, cell_c) not in open_bridge_cells:
                return False

            # 4. Kiểm tra Fragile tile (ký hiệu 'F', 'f', hoặc '~'): Cấm đứng thẳng
            # Hiện đoán mò thội:), nào có doc đủ thông tin bỏ bớt ra
            if tile in ("F", "f", "~") and orient == STANDING:
                return False

        return True

    def _apply_switches(
        self,
        occupied_cells: list[tuple[int, int]],
        n_orient: int,
        current_bridges: tuple[bool, ...],
    ) -> tuple[bool, ...]:
        """Kiểm tra và cập nhật trạng thái các cây cầu nếu khối gỗ chạm vào công tắc."""
        new_bridges = list(current_bridges)

        for cell in occupied_cells:
            if cell in self.switches:
                for sw in self.switches[cell]:
                    sw_type = sw["type"]
                    # Soft switch ('o'): chạm bất kỳ phần nào cũng kích hoạt
                    # Heavy switch ('x'): chỉ kích hoạt khi khối gỗ ĐỨNG (STANDING)
                    if sw_type == "soft" or (sw_type == "heavy" and n_orient == STANDING):
                        mode = sw["mode"]
                        for b_idx in sw["target_indices"]:
                            if mode in ("open", "permanent", "perm"):
                                new_bridges[b_idx] = True
                            elif mode == "close":
                                new_bridges[b_idx] = False
                            elif mode == "toggle":
                                new_bridges[b_idx] = not new_bridges[b_idx]

        result = tuple(new_bridges)
        return current_bridges if result == current_bridges else result
    def _candidates(self, r, c, orient):
        if orient == STANDING:
            return [("U", r - 2, c, VERTICAL), ("D", r + 1, c, VERTICAL),
                    ("L", r, c - 2, HORIZONTAL), ("R", r, c + 1, HORIZONTAL)]
        if orient == HORIZONTAL:
            return [("U", r - 1, c, HORIZONTAL), ("D", r + 1, c, HORIZONTAL),
                    ("L", r, c - 1, STANDING), ("R", r, c + 2, STANDING)]
        return [("U", r - 1, c, STANDING), ("D", r + 2, c, STANDING),
                ("L", r, c - 1, VERTICAL), ("R", r, c + 1, VERTICAL)]

    def step_cost(self, r, c, orient) -> float:
        cost = 1.0
        for cr, cc in self.get_occupied_cells(r, c, orient):
            tile = self.matrix[cr][cc]
            if tile in ("F", "f", "~"):
                return 3.0
            if tile == "=":
                cost = max(cost, 1.5)
        return cost

    
    def get_neighbors(self, state: StateType) -> list[tuple[str, StateType, float]]:
        """
        Sinh danh sách các bước đi hợp lệ tiếp theo: [(action, next_state, step_cost), ...]
        """
        r, c, orient, bridge_states = state

        # Bảng chuyển trạng thái (Orientation Transition Table)
        candidates = self._candidates(r,c, orient)

        valid_moves = []
        for action, nr, nc, n_orient in candidates:
            occupied = self.get_occupied_cells(nr, nc, n_orient)

            # Trước tiên kiểm tra vị trí mới có hợp lệ với trạng thái cầu hiện tại không
            temp_state: StateType = (nr, nc, n_orient, bridge_states)
            if not self.is_valid_state(temp_state):
                continue

            # Nếu khối gỗ đáp xuống an toàn, kiểm tra xem nó có kích hoạt công tắc nào không
            updated_bridges = self._apply_switches(occupied, n_orient, bridge_states)
            next_state: StateType = (nr, nc, n_orient, updated_bridges)

            # Kiểm tra lại lần nữa (phòng trường hợp dẫm công tắc làm đóng chính cây cầu đang đứng)
            if self.is_valid_state(next_state):
                step_cost = self.step_cost(nr, nc, n_orient)
                valid_moves.append((action, next_state, step_cost))

        return valid_moves

    def is_goal(self, state: StateType) -> bool:
        """Kiểm tra chiến thắng: Khối gỗ phải ĐỨNG thẳng ngay tại ô Goal ('G')."""
        r, c, orient, _ = state
        return orient == STANDING and (r, c) == self.goal_pos




    