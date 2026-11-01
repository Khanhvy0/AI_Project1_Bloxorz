import csv
import gc
import os
import re
import statistics
import sys
import time
from glob import glob
 
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
 
from game.level import load_level
from solvers.utils.engine_graph import EngineGraph
from solvers.bfs import BFSSovler
from solvers.dfs import DFSSovler
from solvers.ucs import UCSovler
from solvers.astar import AStarSovler
 
ALGORITHMS = [
    ("BFS", BFSSovler),
    ("DFS", DFSSovler),
    ("UCS", UCSovler),
    ("A*", AStarSovler),
]
 
REPEATS = 5
LEVEL_RANGE = (1, 26)
LEVEL_PATTERN = re.compile(r"^level_(\d+)\.json$")
 
FIELDS = ["Level", "Algorithm", "Time (s)", "Memory (KB)", "Nodes", "Steps", "Cost"]
 
TIME_KEYS = ["time", "search_time", "time_s", "elapsed", "elapsed_time"]
MEMORY_KEYS = ["memory", "memory_peak", "peak_memory", "memory_kb", "peak_memory_kb", "memory_usage"]
NODE_KEYS = ["expanded_nodes", "nodes", "expanded"]
PATH_KEYS = ["path", "actions", "moves"]
COST_KEYS = ["cost", "total_cost", "path_cost"]
 
 
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
 
 
def run_benchmark():
    level_files = select_levels()
    print(f"[INFO] Found {len(level_files)} levels.\n")
 
    results = []
    printed_keys = False
 
    for level_number, file_path in level_files:
        print(f"[PROCESS] Level {level_number}")
 
        for alg_name, alg_class in ALGORITHMS:
            try:
                times = []
                items = None
                for _ in range(REPEATS):
                    agent = alg_class(graph=EngineGraph(load_level(file_path)))
                    gc.collect()
 
                    start = time.perf_counter()
                    stats = agent.search() if hasattr(agent, "search") else agent.solve()
                    elapsed = time.perf_counter() - start
 
                    run_items = stat_items(stats)
                    times.append(read_stat(run_items, TIME_KEYS, elapsed))
                    if items is None:
                        items = run_items
 
                if not printed_keys:
                    print(f"    [DEBUG] stats keys: {list(items.keys())}")
                    printed_keys = True
 
                path = read_stat(items, PATH_KEYS, [])
                results.append({
                    "Level": level_number,
                    "Algorithm": alg_name,
                    "Time (s)": round(statistics.median(times), 4),
                    "Memory (KB)": read_memory(items),
                    "Nodes": read_stat(items, NODE_KEYS, 0),
                    "Steps": len(path) if path else -1,
                    "Cost": read_cost(items),
                })
            except Exception as e:
                print(f"    [ERROR] {alg_name} on level {level_number}: {e}")
                results.append({field: "Error" for field in FIELDS}
                               | {"Level": level_number, "Algorithm": alg_name})
 
    if all(r["Cost"] in ("", "Error") for r in results):
        print("[WARNING] Solvers did not return any cost value; Cost column is empty.")
 
    csv_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.csv")
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)
 
    print(f"\n[SUCCESS] Results saved to: {csv_file}")
 
 
if __name__ == "__main__":
    run_benchmark()
