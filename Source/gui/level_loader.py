"""Đọc file level JSON của nhóm (thư mục levels/) và đổi sang dạng GUI/mock dùng.

Ký hiệu trong file level của nhóm:
  '#' void | '.' floor | '=' bridge | 'S' start | 'G' goal | 'o' soft switch | 'x' heavy switch | 's' split switch
Vị trí start/goal lấy từ chữ 'S' và 'G' trong grid (file không có khóa riêng).
Công tắc: lấy từ danh sách "switches" (grid chỉ đánh dấu chỗ đặt công tắc).
"""
import json
import pathlib

LEVELS_DIR = pathlib.Path(__file__).resolve().parent.parent / "levels"

# ký hiệu của nhóm -> ký hiệu nội bộ của GUI ('.' void, 'o' floor, 'f' fragile, 'g' goal, 'b' bridge)
SYMBOLS = {"#": ".", ".": "o", "=": "b", "S": "o", "G": "g", "F": "f", "o": "o", "x": "o", "s": "o"}


def normalize(raw, level_id):
    rows = raw["grid"]
    if len({len(line) for line in rows}) != 1:
        raise ValueError(f"{level_id}: các hàng của grid không cùng độ dài")

    grid, start, goal = [], None, None
    for r, line in enumerate(rows):
        out = []
        for c, ch in enumerate(line):
            if ch not in SYMBOLS:
                raise ValueError(f"{level_id}: ký hiệu lạ '{ch}' tại hàng {r}, cột {c}")
            if ch == "S":
                start = [r, c]
            elif ch == "G":
                goal = [r, c]
            out.append(SYMBOLS[ch])
        grid.append("".join(out))

    start, goal = raw.get("start", start), raw.get("goal", goal)
    if start is None or goal is None:
        raise ValueError(f"{level_id}: thiếu ô 'S' (start) hoặc 'G' (goal)")

    bridges = raw.get("bridges", {})
    listed = {tuple(c) for b in bridges.values() for c in b["cells"]}
    for r, line in enumerate(grid):
        for c, ch in enumerate(line):
            if ch == "b" and (r, c) not in listed:
                raise ValueError(f"{level_id}: ô cầu '=' tại ({r},{c}) không thuộc bridge nào")
    for r, c in listed:
        if grid[r][c] != "b":
            raise ValueError(f"{level_id}: bridge khai báo tại ({r},{c}) nhưng grid không phải '='")

    return {
        "id": level_id,
        "name": raw.get("name", level_id),
        "group": raw.get("group", "basic"),
        "grid": grid,
        "start": start,
        "goal": goal,
        "bridges": bridges,
        "switches": raw.get("switches", []),
    }


def load_levels(directory=LEVELS_DIR):
    levels = {}
    for path in sorted(pathlib.Path(directory).glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        levels[path.stem] = normalize(raw, path.stem)
    return levels
