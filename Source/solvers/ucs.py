from solvers.utils.sovler import SolverBaseModel, SolverResult, solve_level_raw
from solvers.utils.searches import ucs_search
from utils.measure import measured_solver


# Lưu ý: tên class là UCSovler không phải là UCSSolver( chỉ có 1 chữ S, convention:))
class UCSovler(SolverBaseModel):
    """Class giải tìm đường đi từ đồ thị được cung cấp bằng **thuật toán UCS( uniform cost search)**

    Args:
        graph: đồ thị của mê cung (EngineGraph).
    """
    def __init__(self, graph):
        super().__init__(graph, ucs_search)

    def search(self) -> SolverResult:
        return super().solve()


@measured_solver
def solve(level):
    """API TV1: trả (list[Direction] | None, stats chuẩn). Chi phí lấy từ game.engine.cost."""
    return solve_level_raw(UCSovler, level)
