from functools import partial
from solvers.utils.sovler import SolverBaseModel, SolverResult
from solvers.utils.graph import MazeGraph
from solvers.utils.searches import a_star_search


class AStarSovler(SolverBaseModel):
    """Thuật toán giải tìm đi cho mê cung dựa trên công thức Heuristic
    **Công thức:** `f(x) = g(x) + h(x)`

    Args:
        graph (dict): đồ thị của mê cung cần giải
        heurisitc (str): tên hàm heuristic được sử dụng.
    """

    def __init__(self, graph: MazeGraph, heuristic: str = "pose"):
        solver_func = partial(a_star_search, heuristic=heuristic)
        super().__init__(graph, solver_func)

    def search(self) -> SolverResult:
        return super().solve()



