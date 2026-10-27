"""Adapter Graph cho engine TV1, giữ nguyên State gồm bridges/split/active."""

from game import engine
from game.state import Direction


ACTION_TO_DIRECTION = {
    "U": Direction.UP, "D": Direction.DOWN,
    "L": Direction.LEFT, "R": Direction.RIGHT,
    "S": Direction.SWITCH,  # đổi khối khi đang ở chế độ split
}
DIRECTION_TO_ACTION = {direction: action for action, direction in ACTION_TO_DIRECTION.items()}


class EngineGraph:
    """Cùng API start_state/is_goal/get_neighbors với MazeGraph của TV3.

    Dùng adapter này khi chạy chung với game/GUI; mọi luật và cost lấy từ TV1.
    MazeGraph vẫn dùng được độc lập với luật và cost riêng của TV3.
    """

    def __init__(self, level):
        self.level = level
        self.name = level.name
        self.start_state = engine.initial_state(level)
        self.goal_pos = level.goal

    def is_goal(self, state):
        return engine.is_goal(self.level, state)

    def get_neighbors(self, state):
        return [
            (DIRECTION_TO_ACTION[direction], next_state,
             engine.cost(self.level, state, direction, next_state))
            for direction, next_state in engine.get_successors(self.level, state)
        ]
