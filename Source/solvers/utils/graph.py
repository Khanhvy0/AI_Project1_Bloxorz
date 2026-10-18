# File này chứa các chức năng
# Dựa vào file JSON được cung cấp để xây dựng thành đồ thị cho mê cung

# Ý tưởng chính:
# Đồ thị được tạo thành từ 2 đồ thị con
#   Đồ thị con 1: chứa các vị trí mà khi ở đó thì hình chữ nhật ở trạng thái `Đứng`
#   Đồ thị con 2: chứa các vị trí mà khi ở đó thì hình chữ nhật ở trạng thái `Nằm`
# Đồ thị lớn là một đồ thị lưỡng phân vô hướng và theo giả định hiện tại, trọng số mỗi cạnh bằng 1
import json
from typing import Any


# Đỉnh( vertex) của đồ thị
# inVerticies: dict {(đỉnh kế tiếp, trạng thái của hình chữ nhật): trọng số}
# out_vertices: dict {(đỉnh trước đó, trạng thái của hình chữ nhật): trọng số}
class GraphNode:
    def __int__(self, x: int, y: int):
        self.in_vertices = dict()
        self.out_vertices = dict()
        self.x = x
        self.y = y

        
    def __getattr__(self, name: str):
        if name == "in_vertices":
            return self.in_vertices
        elif name == "out_vertices":
            return self.out_vertices

        raise ValueError(f"No attr named `{name}` exists in GraphNode instance")

    
    def __in_vertices__(self):
        return self.in_vertices
    def __out_vertices__(self):
        return self.out_vertices(self)

    def set_in_vertex(self, sour: Any, weight: float):
        self.in_vertices[sour] = weight 
    def set_out_vertex(self, dest: Any, weight: float):
        self.out_vertices[dest] = weight


# Đồ thị của mê cung
# source: tên file chứa thông tin level
#       Nên sử dụng đường dẫn từ thư mục gốc của đồ án
# graph: đồ thị lớn
class MazeGraph:
    def __init__(self, json_source: str):
        self.source = json_source
        self.graph = dict()         # đồ thị lớn
        self.shape = list()

        self._build_graph()


    # Xây dựng đồ thị
    # Phương pháp xây dựng: tạo 2 đồ thị con rồi kết nối từng đỉnh của chúng lại với nhau
    # Lưu ý: đồ thị lớn là một đồ thị lưỡng phân
    def _build_graph(self):
        """Xây dựng đồ thị cho mê cung được lưu trong file **JSON** khai báo trước"""
        pass





