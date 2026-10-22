from solvers.utils.sovler import SolverBaseModel, SolverResult
from solvers.utils.graph import MazeGraph
from solvers.utils.searches import ucs_search



# Lưu ý: tên class là UCSovler không phải là UCSSolver( chỉ có 1 chữ S, convention:))
class UCSovler(SolverBaseModel):
    """Class giải tìm đường đi từ đồ thị được cung cấp bằng **thuật toán UCS( uniform cost search)**
    
    Args:
        graph (dict): đồ thị của mê cung.
    """
    def __init__(self, graph: MazeGraph):
        super().__init__(graph, ucs_search)

    def search(self) -> SolverResult:
        return super().solve()





