"""Chuyển dữ liệu Bloxorz GBA sang JSON TV1, không đổi luật công tắc."""
import json
from copy import deepcopy
from pathlib import Path


def convert(source, name, toggle_switches=()):
    if source.get("splits") or any("v" in row for row in source["tiles"]):
        raise ValueError("split")
    source = deepcopy(source)
    for key in toggle_switches:
        targets = source["switches"][key]
        if {item[2] for item in targets} != {"on", "off"}:
            raise ValueError("Chỉ biên lại công tắc có cả on và off")
        tiles = [list(row) for row in source["tiles"]]
        for x, y, mode in targets:
            # Hai nhánh có trạng thái đối nhau để toggle đổi lộ trình.
            chars = {"l": "k", "r": "q", "k": "k", "q": "q"} if mode == "off" else {
                "l": "l", "r": "r", "k": "l", "q": "r"}
            tiles[y][x] = chars[tiles[y][x]]
        source["tiles"] = ["".join(row) for row in tiles]
        source["switches"][key] = [[x, y, "onoff"] for x, y, _ in targets]
    switches = source.get("switches", {})
    if any(len({item[2] for item in targets}) != 1 for targets in switches.values()):
        raise ValueError("mixed_switch_modes")
    chars = {" ": "#", "b": ".", "e": "G", "f": "F", "s": "o", "h": "x",
             "l": "=", "r": "=", "k": "=", "q": "="}
    grid = [[chars[tile] for tile in row] for row in source["tiles"]]
    x, y = source["spawn"]
    if grid[y][x] != ".":
        raise ValueError("Spawn phải nằm trên floor")
    grid[y][x] = "S"
    bridges, positions = {}, {}
    for r, row in enumerate(source["tiles"]):
        for c, tile in enumerate(row):
            if tile in "lrkq":
                bid = f"b{len(bridges) + 1}"
                bridges[bid] = {"cells": [[r, c]], "open": tile in "kq"}
                positions[r, c] = bid
    result = {"name": name, "grid": ["".join(row) for row in grid],
              "bridges": bridges, "switches": []}
    for key, targets in switches.items():
        # Khóa nguồn là x * 10 + y, không phải chỉ số theo hàng.
        c, r = divmod(int(key), 10)
        kind = {"o": "soft", "x": "heavy"}[grid[r][c]]
        mode = {"onoff": "toggle", "on": "open", "off": "close"}[targets[0][2]]
        result["switches"].append({
            "pos": [r, c], "type": kind, "mode": mode,
            "targets": [positions[y, x] for x, y, _ in targets],
        })
    return result


if __name__ == "__main__":
    import argparse
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from game import Level

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_file", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    selection = json.loads(Path(__file__).with_name("reference").joinpath("selection.json").read_text())
    sources = json.loads(args.source_file.read_text(encoding="utf-8"))["levels"]
    results = []
    for item in selection:
        result = convert(sources[item["source_stage"] - 1], f'level_{item["level"]:02}',
                         item.get("toggle_switches", ()))
        Level.from_dict(result)
        results.append(result)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for result in results:
        (args.output_dir / f'{result["name"]}.json').write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Converted {len(results)} levels to {args.output_dir}")
