from solvers.utils.sovler import SolverBaseModel
from solvers.utils.graph import MazeGraph



def ucs_search():
    pass

# Lưu ý: tên class là UCSovler không phải là UCSSolver( chỉ có 1 chữ S, convention:))
class UCSovler(SolverBaseModel):
    """Class giải tìm đường đi từ đồ thị được cung cấp bằng **thuật toán UCS( uniform cost search)**"""
    def __init__(self, graph: MazeGraph,
                x_start: int,
                y_start: int,
                rec_state: int):
        super().__init__(graph, x_start, y_start, rec_state, ucs_search)



    def search():
        return super().search()






