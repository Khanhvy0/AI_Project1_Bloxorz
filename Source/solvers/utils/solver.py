
from dataclasses import dataclass
from typing import Callable, Union

from game.level import Level, load_level
from game.state import ACTION_TO_DIRECTION, DIRECTION_TO_ACTION, Direction
from solvers.utils.searches import (
    _check_is_goal,
    _get_start_state,
    _iter_neighbors,
)
from utils.measure import _measure_runs


def _normalize_target(level_or_graph: Union[Level, dict, str]):
    """Chuyển đổi dict hoặc đường dẫn file thành Level; giữ nguyên nếu là Level hoặc mock graph."""
    if isinstance(level_or_graph, Level):
        return level_or_graph
    if isinstance(level_or_graph, dict):
        return Level.from_dict(level_or_graph)
    if isinstance(level_or_graph, str):
        return load_level(level_or_graph)
    if hasattr(level_or_graph, "level") and isinstance(level_or_graph.level, Level):
        return level_or_graph.level
    return level_or_graph


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
        self.graph = _normalize_target(graph)
        self.level = self.graph
        self.solver_func = solver_func

    def run_search(self):
        """Chạy một lần, không đo; dùng chung cho solve() và benchmark."""
        raw_actions, expanded = self.solver_func(self.graph)
        start = _get_start_state(self.graph)

        # [] khi vô nghiệm; phân biệt với lời giải rỗng tại goal ban đầu.
        solved = raw_actions is not None and (
            bool(raw_actions) or _check_is_goal(self.graph, start)
        )
        if not solved:
            return None, {"expanded_nodes": expanded, "solution_cost": 0.0}

        # Chuẩn hóa action về chuỗi ("U", "D", "L", "R", "S") và cộng cost từ engine
        state = start
        total_cost = 0.0
        actions: list[str] = []

        for raw_act in raw_actions:
            action = (
                DIRECTION_TO_ACTION[raw_act]
                if isinstance(raw_act, Direction)
                else raw_act
            )
            for move, next_state, step_cost in _iter_neighbors(self.graph, state):
                if move == action:
                    state = next_state
                    total_cost += step_cost
                    actions.append(action)
                    break
            else:
                raise ValueError(f"Thuật toán trả nước đi không hợp lệ: {raw_act}")

        if not _check_is_goal(self.graph, state):
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


def solve_level_raw(solver_class, level: Level, **kwargs):
    """Adapter giữ API TV1: Level -> (list[Direction] | None, stats chưa đo)."""
    solver = solver_class(level, **kwargs)
    actions, stats = solver.run_search()
    path = (
        None
        if actions is None
        else [ACTION_TO_DIRECTION[action] for action in actions]
    )
    return path, stats