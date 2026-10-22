# Màn chơi và tích hợp TV2

Các màn TV2 dùng JSON của `game.level.load_level`. Giữ nguyên các file
`level_01.json`–`level_07.json` của TV1.

## Các nhóm

- `g1_01.json`–`g1_04.json`: sàn, hố, goal; 3×4 đến 15×15.
- `g2_01.json`–`g2_03.json`: thêm fragile.
- `g3_01.json`–`g3_03.json`: soft/heavy switch và bridge.
- `g4_01.json`–`g4_03.json`: fragile kết hợp switch/bridge.
- `edge_cases/g1_00_nosol.json`: cố ý vô nghiệm, đặt riêng vì test TV1 mặc
  định mọi JSON ở ngay thư mục levels đều có lời giải.

Ký hiệu: # = hố, F = fragile, = = cầu, o = soft switch, x = heavy switch.
Mỗi ô cầu thuộc một nhóm trong bridges, switches[].targets trỏ tới ID nhóm cầu.
Các cầu TV2 ban đầu đóng.

## Mức kiểm chứng

- Với engine TV1: g1/g2 giải được bằng BFS và replay tới goal. Với g3/g4, chỉ
  kiểm chứng bố cục khi mọi cầu mở, do TV1 chưa có logic switch. Riêng g3_01
  chưa giải được khi cầu đóng; khi mở cầu, có lời giải 8 bước.
- Với MazeGraph của TV3: g3/g4 đã được giải và replay với switch hoạt động;
  kiểm tra BFS/UCS/A*. Điều này chưa xác nhận các màn chạy được bằng engine TV1.
- Chưa thêm màn split vì cả hai backend chưa hỗ trợ đầy đủ tách/ghép.

## Cách chạy

Từ Source:

```powershell
python -m unittest tests.test_solvers_tv2 tests.test_solver_integration -v
```

API TV1 vẫn hoạt động:

```python
from game.level import load_level
from solvers.bfs import solve
from utils.measure import measure

level = load_level("levels/g1_01.json")
path, stats = solve(level)
print([direction.name for direction in path] if path is not None else None)
print(stats)
print(measure(solve, level, algorithm="BFS", repeats=5))
```

BFS/DFS/IDS hiện kế thừa cùng SolverBaseModel với UCS/A*.
Xem `../solvers/Convention.md` để gọi thống nhất cả bốn lớp và chọn backend.

Stats API TV1: time_ms, memory_kb, expanded_nodes, solution_length, solution_cost.
Vô nghiệm: path = None, length = -1, cost = 0. Goal không tính vào expanded.
Công cụ measure giữ 7 cột cho TV5: level, algorithm, solved, time_s,
peak_mem_kb, expanded, length. Time và memory đo ở hai lượt riêng.

## Điểm TV1 cần xử lý

File game/__init__.py đã được bạn bổ sung export, lỗi import cũ đã hết.
Test `tests.test_loader.Loader.test_fixture_levels_load_and_solvable` vẫn
thất bại ở `tests/fixtures/level_02.json`: màn cần switch để mở cầu nhưng engine
TV1 chưa kích hoạt switch. Không sửa fixture/test TV1 để làm mất dấu lỗi này.

Tài liệu TV1 còn lệch code ở tile_at (nhận tuple và trả Tile), is_bridge_open
(chưa có) và so sánh thứ tự State. UCS/A* của TV3 đã dùng tie_breaker nên không
cần State có thứ tự khi chạy qua EngineGraph.
