import csv
import gc
import os
import re
import statistics
import sys
import time
from functools import partial
from glob import glob
 
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
 
from game.level import load_level
from solvers.utils.engine_graph import EngineGraph
from solvers.bfs import BFSSovler
from solvers.ucs import UCSovler
from solvers.dfs import IDSSovler
from solvers.astar import AStarSovler
 
# Nhóm dùng IDS thay cho DFS (đề cho phép, cần nêu rõ trong báo cáo).
# "A*" là A* dùng Pose Heuristic. Tên bắt đầu bằng "A*" được kiểm tra
# tính tối ưu so với UCS.
ALGORITHMS = [
    ("BFS", BFSSovler),
    ("IDS", IDSSovler),
    ("UCS", UCSovler),
    ("A*", partial(AStarSovler, heuristic="pose")),
]
 
REFERENCE_ALGORITHM = "UCS"
COST_TOLERANCE = 1e-9
 
REPEATS = 5                  # số lần chạy mỗi thuật toán, lấy trung vị thời gian
SLOW_REPEATS = {"IDS": 1}    # IDS mở rất nhiều node nên chỉ đo 1 lần
LEVEL_RANGE = (1, 26)
LEVEL_PATTERN = re.compile(r"^level_(\d+)\.json$")
 
FIELDS = ["Level", "Algorithm", "Time (s)", "Memory (KB)", "Nodes", "Steps", "Cost"]
 
TIME_KEYS = ["time", "search_time", "time_s", "elapsed", "elapsed_time"]
MEMORY_KEYS = ["memory", "memory_peak", "peak_memory", "memory_kb", "peak_memory_kb", "memory_usage"]
NODE_KEYS = ["expanded_nodes", "nodes", "expanded"]
PATH_KEYS = ["path", "actions", "moves"]
COST_KEYS = ["cost", "total_cost", "path_cost", "solution_cost"]
 
 
def stat_items(stats):
    if isinstance(stats, dict):
        return stats
    try:
        return vars(stats)
    except TypeError:
        return {k: getattr(stats, k) for k in dir(stats)
                if not k.startswith("_") and not callable(getattr(stats, k))}
 
 
def read_stat(items, keys, default=None):
    for key in keys:
        if items.get(key) is not None:
            return items[key]
    return default
 
 
def read_time(items, fallback):
    """Ưu tiên thời gian solver tự báo (giây); nếu chỉ có ms thì đổi sang giây."""
    value = read_stat(items, TIME_KEYS)
    if value is not None:
        return value
    ms = items.get("search_time_ms")
    if ms is not None:
        return ms / 1000.0
    return fallback
 
 
def read_memory(items):
    value = read_stat(items, MEMORY_KEYS)
    if value is not None:
        return value
    for key, val in items.items():
        if "mem" in key.lower() and isinstance(val, (int, float)):
            return val
    return 0
 
 
def read_cost(items):
    value = read_stat(items, COST_KEYS)
    if value is not None:
        return value
    for key, val in items.items():
        if "cost" in key.lower() and isinstance(val, (int, float)):
            return val
    return ""
 
 
def select_levels():
    low, high = LEVEL_RANGE
    selected = []
    for path in sorted(glob(os.path.join(BASE_DIR, "levels", "*.json"))):
        match = LEVEL_PATTERN.match(os.path.basename(path))
        if match and low <= int(match.group(1)) <= high:
            selected.append((int(match.group(1)), path))
    return selected
 
 
def run_one(alg_factory, file_path, repeats=REPEATS):
    """Chạy một thuật toán `repeats` lần trên một màn, trả về (stats, dòng kết quả)."""
    times = []
    items = None
    for _ in range(repeats):
        agent = alg_factory(graph=EngineGraph(load_level(file_path)))
        gc.collect()
 
        start = time.perf_counter()
        stats = agent.search() if hasattr(agent, "search") else agent.solve()
        elapsed = time.perf_counter() - start
 
        run_items = stat_items(stats)
        times.append(read_time(run_items, elapsed))
        if items is None:
            items = run_items
 
    solved = items.get("solved", True)
    path = read_stat(items, PATH_KEYS, [])
    return items, {
        "Time (s)": round(statistics.median(times), 4),
        "Memory (KB)": read_memory(items),
        "Nodes": read_stat(items, NODE_KEYS, 0),
        "Steps": len(path) if (solved and path) else -1,
        "Cost": read_cost(items) if solved else "",
    }
 
 
def check_optimality(results):
    """So cost của mọi biến thể A* với UCS trên từng màn.
 
    Chỉ kết luận khi cả hai đều có cost số hợp lệ; nếu thiếu dữ liệu
    (lỗi, không giải được) thì báo riêng, không coi là "trùng".
    """
    by_level = {}
    for r in results:
        by_level.setdefault(r["Level"], {})[r["Algorithm"]] = r["Cost"]
 
    astar_names = [name for name, _ in ALGORITHMS if name.startswith("A*")]
    compared = {name: 0 for name in astar_names}
    mismatched = {name: [] for name in astar_names}
    missing = {name: [] for name in astar_names}
 
    for level, costs in sorted(by_level.items()):
        ref = costs.get(REFERENCE_ALGORITHM)
        for name in astar_names:
            other = costs.get(name)
            if not isinstance(ref, (int, float)) or not isinstance(other, (int, float)):
                missing[name].append(level)
                continue
            compared[name] += 1
            if abs(other - ref) > COST_TOLERANCE:
                mismatched[name].append((level, other, ref))
 
    print("\n[OPTIMALITY] So sánh cost với", REFERENCE_ALGORITHM)
    for name in astar_names:
        print(f"  {name}: so sánh được {compared[name]} màn, "
              f"lệch {len(mismatched[name])}, thiếu dữ liệu {len(missing[name])}")
        for level, other, ref in mismatched[name]:
            print(f"    [WARNING] Level {level}: cost = {other} != {REFERENCE_ALGORITHM} cost = {ref}")
        if missing[name]:
            print(f"    [SKIP] Không có cost hợp lệ ở level: {missing[name]}")
 
 
def run_benchmark():
    level_files = select_levels()
    print(f"[INFO] Found {len(level_files)} levels.\n")
 
    results = []
    errors = {}          # (algorithm, message) -> [levels]
    printed_keys = False
 
    for level_number, file_path in level_files:
        print(f"[PROCESS] Level {level_number}")
 
        for alg_name, alg_factory in ALGORITHMS:
            try:
                repeats = SLOW_REPEATS.get(alg_name, REPEATS)
                items, row = run_one(alg_factory, file_path, repeats)
 
                if not printed_keys:
                    print(f"    [DEBUG] stats keys: {list(items.keys())}")
                    printed_keys = True
 
                results.append({"Level": level_number, "Algorithm": alg_name, **row})
            except Exception as e:
                key = (alg_name, f"{type(e).__name__}: {e}")
                if key not in errors:
                    print(f"    [ERROR] {alg_name} on level {level_number}: {key[1]}")
                errors.setdefault(key, []).append(level_number)
                results.append({field: "Error" for field in FIELDS}
                               | {"Level": level_number, "Algorithm": alg_name})
 
    if all(r["Cost"] in ("", "Error") for r in results):
        print("[WARNING] Solvers did not return any cost value; Cost column is empty.")
    else:
        check_optimality(results)
 
    if errors:
        print("\n[SUMMARY] Các lỗi gặp phải (mỗi lỗi chỉ in một lần ở trên):")
        for (alg, message), levels in errors.items():
            print(f"  - {alg}: {message}")
            print(f"    xảy ra ở {len(levels)} màn: {levels}")
 
    csv_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.csv")
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)
 
    print(f"\n[SUCCESS] Results saved to: {csv_file}")
 
 
if __name__ == "__main__":
    run_benchmark()
 