# Màn chơi và tích hợp TV2

Các màn TV2 dùng JSON của `game.level.load_level`. Các level TV2 cơ bản và
fragile được xếp trước; các level TV1 cũ được đánh số tiếp theo.

## Thứ tự level

- `level_01.json`–`level_04.json`: sàn, hố, goal; từ nhỏ đến lớn.
- `level_05.json`–`level_07.json`: thêm fragile.
- `level_08.json`–`level_14.json`: các màn TV1 hiện có.
- `level_15.json`–`level_17.json`: soft/heavy switch và bridge.
- `level_18.json`–`level_20.json`: fragile kết hợp switch/bridge.
- `edge_cases/g1_00_nosol.json`: cố ý vô nghiệm, đặt riêng vì test TV1 mặc
  định mọi JSON ở ngay thư mục levels đều có lời giải.

Ký hiệu: # = hố, F = fragile, = = cầu, o = soft switch, x = heavy switch.
Mỗi ô cầu thuộc một nhóm trong bridges, switches[].targets trỏ tới ID nhóm cầu.
Các cầu TV2 ban đầu đóng.

## Mức kiểm chứng

- Với engine TV1: g1/g2 giải được bằng BFS và replay tới goal. Với g3/g4, chỉ
  kiểm chứng bố cục khi mọi cầu mở, do TV1 chưa có logic switch. Riêng level_15
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

level = load_level("levels/level_01.json")
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

Các test hiện hành bao gồm level fixture và kiểm tra tích hợp trên cả
`level_01`–`level_07` lẫn các màn switch/bridge.
