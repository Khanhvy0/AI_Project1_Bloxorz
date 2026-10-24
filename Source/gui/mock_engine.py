"""Engine GIẢ của TV4, để GUI chạy độc lập khi TV1 chưa xong.

Khi TV1 xong: viết adapter có CÙNG các hàm công khai dưới đây
(list_levels, get_level, initial_state, apply_move, solve) rồi đổi import trong server.py.

Quy ước dữ liệu (đề xuất, cần TV1 xác nhận ở CP1):
  state = {"blocks": [[[r,c], ...], ...],   # 1 khối (1-2 ô) hoặc 2 khối lập phương khi split
           "active": 0,                     # khối đang điều khiển (chỉ có nghĩa khi split)
           "bridges": {"b1": false},        # true = đang mở
           "status": "playing" | "won" | "lost"}
  action = "up" | "down" | "left" | "right" | "swap"
  grid (nội bộ, sau khi level_loader đổi): '.' void | 'o' floor | 'f' fragile | 'g' goal | 'b' bridge
"""
import time
import tracemalloc
from collections import deque

from gui.level_loader import load_levels

DIRS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}

LEVELS = load_levels()   # đọc mọi file levels/*.json


def list_levels():
    return [{"id": l["id"], "name": l["name"], "group": l["group"]} for l in LEVELS.values()]


def get_level(level_id):
    return LEVELS[level_id]


def initial_state(level):
    return {
        "blocks": [[list(level["start"])]],
        "active": 0,
        "bridges": {bid: b["open"] for bid, b in level["bridges"].items()},
        "status": "playing",
    }


def _tile(level, r, c, bridges):
    rows = level["grid"]
    if r < 0 or c < 0 or r >= len(rows) or c >= len(rows[0]):
        return None
    ch = rows[r][c]
    if ch == ".":
        return None
    if ch == "b":
        for bid, b in level["bridges"].items():
            if [r, c] in b["cells"]:
                return "o" if bridges[bid] else None
        return None
    return ch


def _roll(cells, d):
    dr, dc = DIRS[d]
    cells = sorted(cells)
    if len(cells) == 1:                      # đứng -> nằm
        r, c = cells[0]
        return [(r + dr, c + dc), (r + 2 * dr, c + 2 * dc)]
    (r1, c1), (r2, c2) = cells
    along = (r1 != r2 and dr != 0) or (c1 != c2 and dc != 0)
    if along:                                # nằm dọc theo hướng lăn -> đứng
        return [(r2 + dr, c2 + dc)] if (dr, dc) in ((1, 0), (0, 1)) else [(r1 + dr, c1 + dc)]
    return [(r1 + dr, c1 + dc), (r2 + dr, c2 + dc)]   # nằm ngang hướng lăn -> trượt sang


def apply_move(level, state, action):
    if state["status"] != "playing":
        return state
    blocks = [[tuple(c) for c in b] for b in state["blocks"]]
    active = state["active"]
    bridges = dict(state["bridges"])
    if action == "swap":
        if len(blocks) == 2:
            active = 1 - active
        return {**state, "active": active}

    new = sorted(_roll(blocks[active], action))
    blocks[active] = new
    status = "playing"
    tiles = [_tile(level, r, c, bridges) for r, c in new]
    if any(t is None for t in tiles):
        status = "lost"                      # rơi khỏi bàn / qua void / cầu đóng
    elif len(new) == 1 and tiles[0] == "f":
        status = "lost"                      # đứng trên ô dễ vỡ
    else:
        for sw in level["switches"]:
            if tuple(sw["pos"]) not in new:
                continue
            if sw["type"] == "heavy" and len(new) != 1:
                continue                     # heavy: chỉ kích hoạt khi khối ĐỨNG
            if sw["type"] == "split":
                continue                     # split: mock chưa hỗ trợ (TV1 làm)
            mode = sw.get("mode", "toggle")
            for bid in sw["targets"]:
                if mode == "toggle":
                    bridges[bid] = not bridges[bid]
                elif mode == "open":
                    bridges[bid] = True
                elif mode == "close":
                    bridges[bid] = False
        if len(new) == 1 and list(new[0]) == level["goal"]:
            status = "won"
    return {"blocks": [[list(c) for c in b] for b in blocks],
            "active": active, "bridges": bridges, "status": status}


def _key(s):
    return (tuple(tuple(map(tuple, b)) for b in s["blocks"]), s["active"],
            tuple(sorted(s["bridges"].items())))


def solve(level, algo):
    """BFS giả cho mọi thuật toán. Thay bằng solver thật của TV2/TV3."""
    tracemalloc.start()
    t0 = time.perf_counter()
    start = initial_state(level)
    frontier, seen, expanded, found = deque([(start, [])]), {_key(start)}, 0, None
    while frontier and found is None:
        s, path = frontier.popleft()
        expanded += 1
        for a in DIRS:
            n = apply_move(level, s, a)
            if n["status"] == "lost":
                continue
            if n["status"] == "won":
                found = path + [a]
                break
            k = _key(n)
            if k not in seen:
                seen.add(k)
                frontier.append((n, path + [a]))
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return {"path": found, "algo": algo,
            "stats": {"search_time_ms": round((time.perf_counter() - t0) * 1000, 3),
                      "peak_memory_kb": round(peak / 1024, 1),
                      "expanded_nodes": expanded,
                      "solution_length": len(found) if found else None}}
