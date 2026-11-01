from functools import partial
from solvers.utils.sovler import SolverBaseModel, SolverResult, solve_level_raw
from solvers.utils.searches import a_star_search
from utils.measure import measured_solver


class AStarSovler(SolverBaseModel):
    """Thuật toán giải tìm đi cho mê cung dựa trên công thức Heuristic
    **Công thức:** `f(x) = g(x) + h(x)`

    Args:
        graph: đồ thị của mê cung cần giải (EngineGraph)
        heuristic (str): tên hàm heuristic: "pose" (mặc định), "l1", "l2", "chebyshev".
    """

    def __init__(self, graph, heuristic: str = "pose"):
        solver_func = partial(a_star_search, heuristic=heuristic)
        super().__init__(graph, solver_func)

    def search(self) -> SolverResult:
        return super().solve()


@measured_solver
def solve(level, heuristic: str = "pose"):
    """API TV1: trả (list[Direction] | None, stats chuẩn)."""
    return solve_level_raw(AStarSovler, level, heuristic=heuristic)
