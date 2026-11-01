"""BFS kế thừa cùng lớp cha với UCS/A*; vẫn hỗ trợ solve(level) của TV1."""

from solvers.utils.searches import bfs_search
from solvers.utils.solver import SolverBaseModel, solve_level_raw
from utils.measure import measured_solver


class BFSSovler(SolverBaseModel):
    """Giữ cách đặt tên Sovler theo các lớp UCSovler/AStarSovler của TV3."""

    def __init__(self, graph):
        super().__init__(graph, bfs_search)


@measured_solver
def solve(level):
    """API TV1: trả (list[Direction] | None, stats chuẩn)."""
    return solve_level_raw(BFSSovler, level)
