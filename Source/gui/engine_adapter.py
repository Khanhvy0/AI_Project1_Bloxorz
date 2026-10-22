"""Adapt the game rules engine to the JSON interface consumed by the GUI."""
from __future__ import annotations

import time
import tracemalloc
from collections import deque
from pathlib import Path

from game import (
    Direction,
    Level,
    MoveStatus,
    Orient,
    State,
    Tile,
    TRANSITIONS,
    apply_move as rules_apply_move,
    get_successors,
    initial_state as rules_initial_state,
    is_goal,
    load_level,
)


LEVELS_DIR = Path(__file__).resolve().parent.parent / "levels"
LEVELS: dict[str, Level] = {
    path.stem: load_level(str(path)) for path in sorted(LEVELS_DIR.glob("*.json"))
}
DIRECTIONS = {
    "up": Direction.UP,
    "down": Direction.DOWN,
    "left": Direction.LEFT,
    "right": Direction.RIGHT,
}
GUI_TILES = {
    Tile.VOID: ".",
    Tile.FLOOR: "o",
    Tile.GOAL: "g",
    Tile.FRAGILE: "f",
    Tile.BRIDGE: "b",
    Tile.SOFT: "o",
    Tile.HEAVY: "o",
    Tile.SPLIT: "o",
}


def _bridge_map(level: Level, bridges: int) -> dict[str, bool]:
    return {
        bridge_id: bool((bridges >> index) & 1)
        for index, bridge_id in enumerate(level.bridge_ids)
    }


def _to_gui_level(level_id: str, level: Level) -> dict:
    grid = ["".join(GUI_TILES[tile] for tile in row) for row in level.tiles]
    bridges = {
        bridge_id: {
            "cells": [
                [r, c]
                for (r, c), index in level.cell_to_bridge.items()
                if index == bridge_index
            ],
            "open": bool((level.initial_bridges >> bridge_index) & 1),
        }
        for bridge_index, bridge_id in enumerate(level.bridge_ids)
    }
    return {
        "id": level_id,
        "name": level.name,
        "group": "basic",
        "grid": grid,
        "start": list(level.start),
        "goal": list(level.goal),
        "bridges": bridges,
        "switches": level.switches,
    }


def list_levels() -> list[dict[str, str]]:
    return [
        {"id": level_id, "name": level.name, "group": "basic"}
        for level_id, level in LEVELS.items()
    ]


def get_level(level_id: str) -> dict:
    return _to_gui_level(level_id, LEVELS[level_id])


def _to_gui_state(level: Level, state: State, status: str) -> dict:
    return {
        "blocks": [[list(cell) for cell in state.cells()]],
        "active": 0,
        "bridges": _bridge_map(level, state.bridges),
        "status": status,
    }


def _from_gui_state(level: Level, state: dict) -> State:
    if len(state["blocks"]) != 1:
        raise NotImplementedError("Split block states are not implemented in the rules engine")
    cells = tuple(sorted(tuple(cell) for cell in state["blocks"][0]))
    if len(cells) == 1:
        r, c = cells[0]
        orient = Orient.STAND
    elif len(cells) == 2 and cells[0][0] == cells[1][0] and cells[1][1] == cells[0][1] + 1:
        r, c = cells[0]
        orient = Orient.HORIZ
    elif len(cells) == 2 and cells[0][1] == cells[1][1] and cells[1][0] == cells[0][0] + 1:
        r, c = cells[0]
        orient = Orient.VERT
    else:
        raise ValueError(f"Invalid block cells in GUI state: {cells!r}")

    bridges = sum(
        1 << index
        for index, bridge_id in enumerate(level.bridge_ids)
        if state["bridges"].get(bridge_id, False)
    )
    return State(r, c, orient, bridges)


def initial_state(level: dict) -> dict:
    level_id = level["id"]
    return _to_gui_state(LEVELS[level_id], rules_initial_state(LEVELS[level_id]), "playing")


def apply_move(level: dict, state: dict, action: str) -> dict:
    if state["status"] != "playing" or action == "swap":
        return state
    direction = DIRECTIONS[action]
    rules_level = LEVELS[level["id"]]
    current = _from_gui_state(rules_level, state)
    result = rules_apply_move(rules_level, current, direction)
    if result.legal:
        next_state = result.state
        status = "won" if result.status == MoveStatus.WIN else "playing"
    else:
        orient, dr, dc = TRANSITIONS[(current.orient, direction)]
        next_state = State(current.r + dr, current.c + dc, orient, current.bridges)
        status = "lost"
    return _to_gui_state(rules_level, next_state, status)


def solve(level: dict, algo: str) -> dict:
    if algo != "bfs":
        raise ValueError(f"{algo} is not implemented; only BFS is available")

    rules_level = LEVELS[level["id"]]
    start = rules_initial_state(rules_level)
    frontier = deque([start])
    parent = {start: None}
    parent_move: dict[State, Direction] = {}
    expanded = 0
    found = None

    tracemalloc.start()
    start_time = time.perf_counter()
    while frontier:
        state = frontier.popleft()
        expanded += 1
        if is_goal(rules_level, state):
            found = state
            break
        for direction, next_state in get_successors(rules_level, state):
            if next_state in parent:
                continue
            parent[next_state] = state
            parent_move[next_state] = direction
            frontier.append(next_state)

    path = None
    if found is not None:
        path = []
        while parent[found] is not None:
            path.append(parent_move[found].name.lower())
            found = parent[found]
        path.reverse()

    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return {
        "path": path,
        "algo": "bfs",
        "stats": {
            "search_time_ms": round((time.perf_counter() - start_time) * 1000, 3),
            "peak_memory_kb": round(peak / 1024, 1),
            "expanded_nodes": expanded,
            "solution_length": len(path) if path is not None else None,
        },
    }
