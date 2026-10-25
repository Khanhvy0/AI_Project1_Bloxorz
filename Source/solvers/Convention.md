# Quy ước chung TV2 / TV3

Cả bốn lớp dùng `SolverBaseModel` trong `utils/sovler.py`:

```text
SolverBaseModel
├── BFSSovler
├── DFSSovler
├── UCSovler
├── AStarSovler
└── IDSSovler (tùy chọn)
```

Giữ nguyên cách viết `Sovler` và tên file `sovler.py` của TV3 để không làm hỏng
các import đang dùng. Các lớp con chỉ gắn thuật toán trong `utils/searches.py`;
lớp cha xử lý kết quả và đo lường.

## Cách gọi thống nhất

```python
from game.level import load_level
from solvers.utils.engine_graph import EngineGraph
from solvers.bfs import BFSSovler
from solvers.dfs import DFSSovler
from solvers.ucs import UCSovler
from solvers.astar import AStarSovler
from utils.measure import measure

graph = EngineGraph(load_level("levels/level_08.json"))
for solver_class in (BFSSovler, DFSSovler, UCSovler, AStarSovler):
    solver = solver_class(graph)
    result = solver.search()  # solve() có cùng kết quả và cùng cách đo
    print(result.solved, result.actions, result.solution_cost)
    print(measure(solver, repeats=3))
```

`SolverResult` có `actions` (U/D/L/R/SWITCH), `solved`, `solution_length`,
`solution_cost`, `expanded_nodes`, `search_time_ms`, `peak_memory_kb`.
Vô nghiệm: actions = [], solved = False, length = -1, cost = 0.
Nếu ban đầu đã ở goal: actions = [], solved = True, length = 0, expanded = 0.
IDS với giới hạn độ sâu chưa đủ cũng trả solved = False.

Các hàm tìm kiếm nhận graph, trả `(actions, expanded_nodes)`; [] là quy ước
vô nghiệm cũ của TV3, lớp cha phân biệt với trường hợp goal ban đầu.
`expanded_nodes` chỉ tăng khi pop một state không phải goal rồi sinh hàng xóm.
BFS tối ưu số bước, UCS tối ưu tổng cost; DFS không đảm bảo tối ưu.

## Chọn cùng backend khi so sánh

- `EngineGraph(level)`: gọi luật chơi và cost từ TV1, giữ nguyên toàn bộ State
  (bridges, split, active), hỗ trợ switch và split. `SWITCH` đổi khối đang điều
  khiển và tính một bước, cost lấy từ engine. Dùng khi tích hợp với game/GUI.
- `MazeGraph.from_json_file(path)`: backend độc lập của TV3, có soft/heavy switch,
  cost ô thường 1, cầu 1.5, fragile 3. Không tự thay bằng engine TV1.
- Không so sánh các solver chạy trên hai backend khác nhau rồi kết luận về
  thuật toán: luật switch và cost đang khác nhau.
- A* hỗ trợ State của TV1 và tuple state của TV3. Heuristic l1/l2 chia 2 giả định
  mỗi bước dời ô neo tối đa 2 ô và cost >= 1. Với `graph.has_teleports = True`,
  A* dùng h = 0 cho toàn bộ lượt tìm kiếm (kể cả trước split), nên chạy như UCS.
  Nếu TV1 đổi cost xuống dưới 1 thì TV3 cần xem lại heuristic khoảng cách.
- Đã bỏ phạt nằm +0.5 của l1: khối nằm ngang tại (0,1), goal (0,3) chỉ cần
  một lần lăn phải; công thức cũ cho 1.5 nên vượt chi phí thật 1.

## Đo và tương thích API cũ

Lớp cha đo một lượt thời gian không tracemalloc và một lượt bộ nhớ riêng.
`measure(solver, repeats=N)` hoặc `measure(solver.search, repeats=N)` gọi
`run_search()` chưa đo, nên không bị đo lồng nhau. Graph phải chạy lại được
và không thay đổi màn chơi giữa các lần đo.

BFS/DFS/IDS vẫn giữ hàm module `solve(level) -> (path, stats)` cho API TV1.
Hàm này dùng cùng lớp con và adapter; path là list[Direction] hoặc None,
stats giữ 5 trường trong `docs/INTERFACE.md`.
UCS/A* hiện sử dụng API lớp của TV3; gọi chúng với EngineGraph như ví dụ trên.

## Kiểm tra

Từ thư mục Source:

```powershell
python -m unittest tests.test_solvers_tv2 tests.test_solver_integration -v
python -m unittest discover -s tests -t . -v
```

Bộ test tích hợp kiểm tra kế thừa, replay path, vô nghiệm/goal ban đầu,
expanded, tách phép đo, UCS chọn đường rẻ hơn và A* khớp cost của UCS trên các
màn hiện có, gồm màn 21 bắt buộc split, đổi khối, mở cầu và ghép lại.
