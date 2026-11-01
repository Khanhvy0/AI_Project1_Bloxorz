"""Adapter Graph cho engine, giữ nguyên State gồm bridges/split/active."""

from game import engine
from game.level import Tile
from game.state import Direction


ACTION_TO_DIRECTION = {
    "U": Direction.UP, "D": Direction.DOWN,
    "L": Direction.LEFT, "R": Direction.RIGHT,
    "S": Direction.SWITCH,
}
DIRECTION_TO_ACTION = {direction: action for action, direction in ACTION_TO_DIRECTION.items()}


class EngineGraph:
    """Graph duy nhất cho solver: start_state / is_goal / get_neighbors -> (action, state, cost).

    Mọi luật và chi phí lấy từ game.engine (get_successors, is_goal, cost), nên solver, GUI và test
    luôn dùng cùng một bộ luật.
    """

    def __init__(self, level):
        self.level = level
        self.name = level.name
        self.start_state = engine.initial_state(level)
        self.goal_pos = level.goal
        # Có công tắc split: khối bị dịch chuyển nên heuristic theo khoảng cách cần thận trọng
        self.has_split = any(sw.kind == Tile.SPLIT for sw in level.switch_at.values())

    def is_goal(self, state):
        return engine.is_goal(self.level, state)

    def get_neighbors(self, state):
        return [
            (DIRECTION_TO_ACTION[direction], next_state,
             engine.cost(self.level, state, direction, next_state))
            for direction, next_state in engine.get_successors(self.level, state)
        ]