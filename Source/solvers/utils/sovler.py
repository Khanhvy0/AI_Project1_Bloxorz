# Các class hàm giải tìm đường đi nên được xây dựng bằng việc
#       Kế thừa tìm hàm này
from solvers.utils.graph import MazeGraph


class SolverBaseModel:
    def __init__(self, graph: MazeGraph, 
                x_start: int,
                y_start: int,
                rec_state: int,
                solver: function):
        """
            Args:
                graph (MazeGraph): đồ thị cần được giải.
                x_start (int): vị trí bắt đầu trên trục hoành của hình chữ nhật.
                y_start (int): vị trí bắt đầu trên trục tung của hình chữ nhật.
                rec_state (int): trạng thái của hình chữ nhật, 0: đứng, 1: nằm.
        """
        self.graph = graph
        self.x_start = x_start
        self.y_start = y_start
        self.rec_init_state = rec_state
        self.sovler = solver

    def solve(self):
        """Tìm lời giải
        Args:
            None
        Returns:
            + **Danh sách các thao tác cần thực hiện** có dạng **list[str]** để đi từ điểm đầu đến đích
                hoặc **danh sách rỗng nếu không có lời giải**
        """

        path = self.sovler()

    def _path_to_action(self):
        """Chuyển đường đi từ điểm xuất phát đến đích thành các thao tác di chuyển cần thực hiện"""
        pass





