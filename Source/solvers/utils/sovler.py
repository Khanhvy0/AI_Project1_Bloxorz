"""Lớp cha chung: chạy thuật toán, đo riêng thời gian/bộ nhớ và đóng gói kết quả."""

from dataclasses import dataclass
from typing import Callable

from utils.measure import _measure_runs


@dataclass
class SolverResult:
    actions: list[str]
    solution_length: int
    expanded_nodes: int
    search_time_ms: float
    peak_memory_kb: float
    solved: bool = True
    solution_cost: float = 0.0


class SolverBaseModel:
    def __init__(self, graph, solver_func: Callable):
        self.graph = graph
        self.solver_func = solver_func

    def run_search(self):
        """Chạy một lần, không đo; dùng chung cho solve() và benchmark."""
        actions, expanded = self.solver_func(self.graph)
        # TV3 dùng [] khi vô nghiệm; phân biệt với lời giải rỗng tại goal ban đầu.
        solved = actions is not None and (
            bool(actions) or self.graph.is_goal(self.graph.start_state)
        )
        if not solved:
            return None, {"expanded_nodes": expanded, "solution_cost": 0.0}

        # Cộng cost từ chính graph mà thuật toán đã sử dụng.
        state = self.graph.start_state
        total_cost = 0.0
        for action in actions:
            for move, next_state, step_cost in self.graph.get_neighbors(state):
                if move == action:
                    state = next_state
                    total_cost += step_cost
                    break
            else:
                raise ValueError(f"Thuật toán trả nước đi không hợp lệ: {action}")
        if not self.graph.is_goal(state):
            raise ValueError("Đường đi của thuật toán chưa tới goal")
        return actions, {"expanded_nodes": expanded, "solution_cost": total_cost}

    def solve(self) -> SolverResult:
        """Một lượt thời gian và một lượt bộ nhớ riêng, cùng quy ước cho mọi solver."""
        actions, stats = _measure_runs(self.run_search)
        return SolverResult(
            actions=actions if actions is not None else [],
            solution_length=stats["solution_length"],
            expanded_nodes=stats["expanded_nodes"],
            search_time_ms=stats["time_ms"],
            peak_memory_kb=stats["memory_kb"],
            solved=actions is not None,
            solution_cost=stats["solution_cost"],
        )

    def search(self) -> SolverResult:
        return self.solve()


def solve_level_raw(solver_class, level, **kwargs):
    """Adapter giữ API TV1: Level -> (list[Direction] | None, stats chưa đo)."""
    from solvers.utils.engine_graph import EngineGraph, ACTION_TO_DIRECTION

    solver = solver_class(EngineGraph(level), **kwargs)
    actions, stats = solver.run_search()
    path = None if actions is None else [ACTION_TO_DIRECTION[action] for action in actions]
    return path, stats
