from solvers.utils.sovler import SolverBaseModel
from solvers.utils.graph import MazeGraph




def heuristic_func(type: str="l1") -> function:
    pass

def a_star_search():
    pass

class AStarSovler(SolverBaseModel):
    """Thuật toán giải tìm đi cho mê cung dựa trên công thức Heuristic  
            `f(x) = g(x) + h(x)`  
        
    """
    def __init__(self, graph: MazeGraph,
                x_start: int,
                y_start: int,
                rec_state: int,
                heuristic_type: str):
        super().__init__(graph, x_start, y_start, rec_state, a_star_search)
        self.heuristic_func = heuristic_func(heuristic_type)

    def search():
        return super().search()




