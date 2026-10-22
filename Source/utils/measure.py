"""Đo solver theo docs/INTERFACE.md; thời gian và bộ nhớ ở hai lần chạy riêng."""

from functools import wraps
from time import perf_counter
import tracemalloc


def _measure_runs(run, repeats=1):
    """run() trả (path, stats); không bật tracemalloc trong các lượt đo thời gian."""
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 1:
        raise ValueError("repeats phải là số nguyên dương")
    if tracemalloc.is_tracing():
        raise RuntimeError("Hãy tắt tracemalloc trước khi đo thời gian")

    total_time = 0.0
    for _ in range(repeats):
        started = perf_counter()
        path, stats = run()
        total_time += perf_counter() - started

    # Lần chạy riêng, luôn dọn bộ đo kể cả khi solver gặp lỗi.
    tracemalloc.start()
    try:
        run()
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    return path, {
        "time_ms": total_time / repeats * 1000,
        "memory_kb": peak_bytes / 1024,
        "expanded_nodes": stats["expanded_nodes"],
        "solution_length": len(path) if path is not None else -1,
        "solution_cost": float(stats["solution_cost"]),
    }


def measured_solver(search):
    """Thêm stats chuẩn cho BFS/DFS/IDS, giữ cách gọi solve(level).

    Hàm search gốc chỉ cần trả expanded_nodes và solution_cost.
    wraps giữ __wrapped__ để measure() đo phần tìm kiếm, tránh đo lồng nhau.
    """
    @wraps(search)
    def solve(level, *args, **kwargs):
        return _measure_runs(lambda: search(level, *args, **kwargs))

    return solve


def measure(solver_fn, level=None, level_name="", algorithm="", repeats=1):
    """Trả 7 cột cho TV5; dùng được với mọi solver theo interface chung.

    Nhận solver object, bound method search/solve, hoặc hàm solve(level).
    Gọi phần tìm kiếm chưa đo để tránh lồng tracemalloc và đếm sai thời gian.
    Level và solver phải cho phép chạy lại mà không đổi dữ liệu màn chơi.
    """
    owner = getattr(solver_fn, "__self__", solver_fn)
    if callable(getattr(owner, "run_search", None)):
        run = owner.run_search
        name = owner.graph.name
        algorithm_name = type(owner).__name__
    else:
        search = getattr(solver_fn, "__wrapped__", solver_fn)
        run = lambda: search(level)
        name = level.name
        algorithm_name = solver_fn.__module__.rsplit(".", 1)[-1].upper()
    path, stats = _measure_runs(run, repeats)
    return {
        "level": level_name or name,
        "algorithm": algorithm or algorithm_name,
        "solved": path is not None,
        "time_s": stats["time_ms"] / 1000,
        "peak_mem_kb": stats["memory_kb"],
        "expanded": stats["expanded_nodes"],
        "length": stats["solution_length"],
    }
