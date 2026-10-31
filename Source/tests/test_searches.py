# Đo lường, ước lượng thông tin liên quan tới thời gian thực thi,
# dung lượng sử dụng của giải thuật A*
import json
from solvers.utils.graph import MazeGraph
from solvers.utils.sovler import SolverBaseModel
from solvers.ucs import UCSovler
from solvers.astar import AStarSovler
from solvers.bfs import BFSSovler
from solvers.dfs import DFSSovler




def run_test(solver:  SolverBaseModel, repeat: int=10):
    if repeat <= 0:
        raise ValueError()
    # [time in sec, mem in KB, ...]
    sum_stats = {
        'solution_length': 0,
        'expanded_nodes': 0,
        'time_ms': 0.0,
        'memory_kb': 0.0,
        'solution_cost': 0.0
    }

    for _ in range(repeat):
        stats = solver.solve()

        sum_stats['solution_length'] += stats.solution_length
        sum_stats['expanded_nodes'] += stats.expanded_nodes
        sum_stats['time_ms'] += stats.search_time_ms
        sum_stats['memory_kb'] += stats.peak_memory_kb
        sum_stats['solution_cost'] += stats.solution_cost
        
    avg_stats = dict(sum_stats)
    avg_stats['solution_length'] = sum_stats['solution_length'] / repeat
    avg_stats['expanded_nodes'] = sum_stats['expanded_nodes'] / repeat
    avg_stats['time_ms'] = sum_stats['time_ms'] / (1000 *repeat)
    avg_stats['memory_kb'] = sum_stats['memory_kb'] / (1024 * repeat)
    avg_stats['solution_cost'] = sum_stats['solution_cost'] / repeat

    print(avg_stats)
    return avg_stats


def load_json(filepath: str):
    with open(filepath, mode='r') as f:
        level_data = json.load(f)

        return level_data


def test(filepath: str, SolverClass, **kwargs):
    level_data = load_json(filepath)
    level = MazeGraph(level_data)
    if 'heuristic' in kwargs:
        solver = SolverClass(level, heuristic=kwargs['heuristic'])
    else:
        solver = SolverClass(level)

    run_test(solver, 1) # run once since the searching algorithms are deterministic



if __name__ == '__main__':
    # test('levels/generate/open_100x100.json', AStarSovler, heuristic="pose")
    # test('levels/generate/maze_100x100.json', AStarSovler, heuristic="pose")
    # test('levels/generate/open_500x500.json', AStarSovler, heuristic="pose")
    # test('levels/generate/maze_500x500.json', AStarSovler, heuristic="pose")
    # test('levels/generate/open_800x800.json', AStarSovler, heuristic="pose")
    test('levels/generate/maze_800x800.json', AStarSovler, heuristic="pose")
    test('levels/generate/open_800x800_no_route.json', AStarSovler, heuristic="pose")
    # test('levels/generate/open_1000x1000.json', AStarSovler, heuristic="pose")
    # test('levels/generate/open_1000x1000.json', AStarSovler, heuristic="pose")
    # test('levels/generate/maze_1000x1000.json', AStarSovler, heuristic="pose")
    # test('levels/generate/massive_void.json', AStarSovler, heuristic="pose")
    # test('levels/generate/small_void_but_lot.json', AStarSovler, heuristic="pose")