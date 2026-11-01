"""Adapt the game rules engine to the JSON interface consumed by the GUI."""
from __future__ import annotations

from pathlib import Path
from threading import Event

from game import (
    Direction,
    Level,
    MoveStatus,
    Orient,
    State,
    Tile,
    TRANSITIONS,
    apply_move as rules_apply_move,
    initial_state as rules_initial_state,
    load_level,
)
from solvers.astar import AStarSovler
from solvers.bfs import BFSSovler
from solvers.dfs import DFSSovler, IDSSovler
from solvers.ucs import UCSovler
from solvers.utils.engine_graph import ACTION_TO_DIRECTION, EngineGraph


LEVELS_DIR = Path(__file__).resolve().parent.parent / "levels"
LEVELS: dict[str, Level] = {
    path.stem: load_level(str(path)) for path in sorted(LEVELS_DIR.glob("*.json"))
}


class SolveCancelled(Exception):
    """Raised when a solver search is cancelled by the GUI."""


class _CancellableGraph:
    def __init__(self, graph: EngineGraph, cancellation_event: Event):
        self._graph = graph
        self._cancellation_event = cancellation_event

    def __getattr__(self, name):
        return getattr(self._graph, name)

    def _check_cancelled(self):
        if self._cancellation_event.is_set():
            raise SolveCancelled("Solver was stopped")

    def is_goal(self, state):
        self._check_cancelled()
        return self._graph.is_goal(state)

    def get_neighbors(self, state):
        self._check_cancelled()
        return self._graph.get_neighbors(state)


DIRECTIONS = {
    "up": Direction.UP,
    "down": Direction.DOWN,
    "left": Direction.LEFT,
    "right": Direction.RIGHT,
    "switch": Direction.SWITCH,  # dùng khi solver replay qua màn có split
    "swap": Direction.SWITCH,    # phím cách từ GUI người chơi
}
LEVEL_ORDER = [f"level_{n:02d}" for n in range(1, 27)]
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
    ordered_ids = [level_id for level_id in LEVEL_ORDER if level_id in LEVELS]
    return [
        {"id": level_id, "name": LEVELS[level_id].name, "group": "basic"}
        for level_id in ordered_ids
    ]


def get_level(level_id: str) -> dict:
    return _to_gui_level(level_id, LEVELS[level_id])


def _to_gui_state(level: Level, state: State, status: str) -> dict:
    if state.is_split:
        # Hai khối nhỏ riêng biệt, mỗi khối là 1 danh sách 1 ô
        cell_a, cell_b = state.split
        blocks = [[list(cell_a)], [list(cell_b)]]
    else:
        blocks = [[list(cell) for cell in state.cells()]]
    return {
        "blocks": blocks,
        "active": state.active,
        "bridges": _bridge_map(level, state.bridges),
        "status": status,
    }


def _from_gui_state(level: Level, state: dict) -> State:
    bridges = sum(
        1 << index
        for index, bridge_id in enumerate(level.bridge_ids)
        if state["bridges"].get(bridge_id, False)
    )

    if len(state["blocks"]) == 2:
        # Trạng thái tách khối: mỗi block có đúng 1 ô
        cell_a = tuple(state["blocks"][0][0])
        cell_b = tuple(state["blocks"][1][0])
        active_index = state.get("active", 0)
        active_cell = cell_a if active_index == 0 else cell_b
        return State.make_split(cell_a, cell_b, active_cell, bridges)

    # Khối thường: 1 block với 1 hoặc 2 ô
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
    return State(r, c, orient, bridges)


def initial_state(level: dict) -> dict:
    level_id = level["id"]
    return _to_gui_state(LEVELS[level_id], rules_initial_state(LEVELS[level_id]), "playing")


def apply_move(level: dict, state: dict, action: str) -> dict:
    if state["status"] != "playing":
        return state
    direction = DIRECTIONS[action]
    rules_level = LEVELS[level["id"]]
    current = _from_gui_state(rules_level, state)
    result = rules_apply_move(rules_level, current, direction)
    if result.legal:
        next_state = result.state
        status = "won" if result.status == MoveStatus.WIN else "playing"
    elif direction == Direction.SWITCH:
        # SWITCH bị BLOCKED (chưa tách khối) → giữ nguyên state, không thua
        return state
    else:
        orient, dr, dc = TRANSITIONS[(current.orient, direction)]
        next_state = State(current.r + dr, current.c + dc, orient, current.bridges)
        status = "lost"
    return _to_gui_state(rules_level, next_state, status)


def solve(level: dict, algo: str, cancellation_event: Event | None = None) -> dict:
    rules_level = LEVELS[level["id"]]
    solvers = {
        "bfs": BFSSovler,
        "dfs": IDSSovler,
        "ucs": UCSovler,
        "astar": AStarSovler,
    }
    try:
        solver_class = solvers[algo]
    except KeyError:
        raise ValueError(f"Unsupported solver: {algo}") from None

    graph = EngineGraph(rules_level)
    if cancellation_event is not None:
        graph = _CancellableGraph(graph, cancellation_event)
    result = solver_class(graph).solve()
    path = (
        [ACTION_TO_DIRECTION[action].name.lower() for action in result.actions]
        if result.solved
        else None
    )
    return {
        "path": path,
        "algo": algo,
        "stats": {
            "search_time_ms": result.search_time_ms,
            "peak_memory_kb": result.peak_memory_kb,
            "expanded_nodes": result.expanded_nodes,
            "solution_length": result.solution_length if result.solved else None,
        },
    }
