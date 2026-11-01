"""DFS/IDS kế thừa SolverBaseModel, dùng chung cách đo và kết quả với TV3."""

from functools import partial

from solvers.utils.searches import dfs_search, ids_search
from solvers.utils.solver import SolverBaseModel, solve_level_raw
from utils.measure import measured_solver


class DFSSovler(SolverBaseModel):
    """DFS chống lặp bằng toàn bộ state; không đảm bảo lời giải tối ưu."""

    def __init__(self, graph):
        super().__init__(graph, dfs_search)


class IDSSovler(SolverBaseModel):
    def __init__(self, graph, max_depth=200):
        super().__init__(graph, partial(ids_search, max_depth=max_depth))


@measured_solver
def solve(level):
    return solve_level_raw(DFSSovler, level)


@measured_solver
def solve_ids(level, max_depth=200):
    """None nghĩa là chưa tìm thấy lời giải trong giới hạn max_depth."""
    return solve_level_raw(IDSSovler, level, max_depth=max_depth)
