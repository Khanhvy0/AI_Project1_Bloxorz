import time
import tracemalloc
from dataclasses import dataclass
from typing import Callable
from solvers.utils.graph import MazeGraph, StateType


@dataclass
class SolverResult:
    actions: list[str]        # Chuỗi thao tác ['U', 'R', 'D', ...]
    solution_length: int      # Số bước đi = len(actions)
    expanded_nodes: int       # Số lượng trạng thái đã mở rộng
    search_time_ms: float     # Thời gian chạy (mili-giây)
    peak_memory_kb: float     # Bộ nhớ đỉnh (KB)


class SolverBaseModel:
    def __init__(self, graph: MazeGraph, solver_func: Callable):
        """
        Args:
            graph (MazeGraph): Đối tượng mê cung (chứa sẵn start_state và goal_pos).
            solver_func (Callable): Hàm thuật toán từ searches.py.
        """
        self.graph = graph
        self.solver_func = solver_func

    def solve(self) -> SolverResult:
        """Thực thi thuật toán tìm kiếm và tự động đo lường Time, Memory."""
        tracemalloc.start()
        start_time = time.perf_counter()

        # Mọi hàm trong searches.py đều trả về: (danh_sách_action, số_node_đã_duyệt)
        actions, expanded_nodes = self.solver_func(self.graph)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        return SolverResult(
            actions=actions,
            solution_length=len(actions),
            expanded_nodes=expanded_nodes,
            search_time_ms=round(elapsed_ms, 3),
            peak_memory_kb=round(peak_bytes / 1024.0, 2),
        )