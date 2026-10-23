# Đặc tả interface Engine

> Các thành viên khác chỉ cần `from game import ...`.

## 1. Quy ước

- Toạ độ `(r, c)` = (hàng, cột), gốc ở góc trên-trái, `r` tăng xuống dưới.
- `Direction`: `UP, DOWN, LEFT, RIGHT, SWITCH`. `MOVES` = 4 hướng đầu (không gồm `SWITCH`). `Orient`: `STAND, HORIZ, VERT`.
- Ô neo `(r, c)` của khối = ô trên-trái: STAND {(r,c)}, HORIZ {(r,c),(r,c+1)}, VERT {(r,c),(r+1,c)}.

## 2. State & Level

### 2.1. `State` (bất biến, hashable, comparable)

| Trường    | Ý nghĩa                                                                                                                                                      |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `r, c`    | ô neo. Khi đang tách khối luôn là `-1, -1`                                                                                                                   |
| `orient`  | hướng khối (`Orient`). . Khi đang tách khối luôn là `STAND`                                                                                                  |
| `bridges` | bitmask: bit `i = 1` nếu cầu thứ `i` đang mở                                                                                                                 |
| `split`   | `None` nếu là khối thường. Nếu đang tách: `((r1,c1),(r2,c2))` là vị trí hai khối nhỏ, **luôn sắp xếp tăng dần** để mỗi cấu hình vật lý chỉ có đúng một state |
| `active`  | `0` hoặc `1`: khối nhỏ đang điều khiển (chỉ số trong `split`). Khi không tách luôn là `0`                                                                    |

- `state.cells()` trả về tuple các ô `(r, c)` đang bị chiếm: 1 ô (đứng), 2 ô (nằm), hoặc 2 ô của hai khối nhỏ (đang tách).
- `state.is_split` (`bool`) và `state.active_cell` (ô của khối đang điều khiển, `None` nếu không tách).
- `State.make_split(cell_a, cell_b, active_cell, bridges)` tạo state tách khối ở dạng chuẩn (chỉ cần khi viết test).
- Dùng `State` trực tiếp làm key của `set`/`dict`. `State` là `NamedTuple` nên so sánh được thứ tự, đẩy trực tiếp tuple `(cost, state)` vào `heapq` cho UCS / A\* được (hai state khác nhau luôn phân biệt được ở 4 trường đầu hoặc ở `split`, không gây lỗi so sánh `None` với tuple).
- Khi hai khối nhỏ kề nhau, engine tự ghép thành khối 1x1x2 nằm (`HORIZ`/`VERT`, `split = None`).

### 2.2. `Level` (thông tin màn chơi)

| Thuộc tính / Phương thức        | Ý nghĩa                                                                                                                                          |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `level.name`                    | tên màn chơi (`str`)                                                                                                                             |
| `level.rows`, `level.cols`      | kích thước bảng (`int`)                                                                                                                          |
| `level.start`                   | toạ độ `(r, c)` ô xuất phát                                                                                                                      |
| `level.goal`                    | toạ độ `(r, c)` ô đích (dùng tính heuristic cho A\*)                                                                                             |
| `level.tile_at((r, c))`         | trả về `Tile` (enum) tại ô: `VOID, FLOOR, GOAL, FRAGILE, BRIDGE, SOFT, HEAVY, SPLIT`. **Nhận một tuple `(r, c)`**, trả về enum, không phải ký tự |
| `level.in_bounds((r, c))`       | `True` nếu ô nằm trong bảng                                                                                                                      |
| `level.bridge_ids`              | danh sách id cầu theo thứ tự khai báo; vị trí trong list = chỉ số bit trong `state.bridges`                                                      |
| `level.cell_to_bridge`          | `dict`: ô cầu `(r, c)` -> chỉ số bit của cầu đó                                                                                                  |
| `level.initial_bridges`         | bitmask trạng thái cầu lúc đầu                                                                                                                   |
| `level.is_bridge_open(s, r, c)` | `True` nếu ô `(r, c)` là cầu và đang mở ứng với state `s`; `False` nếu đóng hoặc không phải cầu                                                  |
| `level.switch_at`               | `dict`: ô `(r, c)` -> `SwitchInfo` (`pos`, `kind`, `mask`, `mode`, `cubes`), dùng để vẽ/tra công tắc                                             |

`tile_at` và `in_bounds` nhận **một tuple** `(r, c)`; `is_bridge_open` nhận `r, c` rời nhau.

## 3. Hàm cho solver

```python
from game import load_level, initial_state, get_successors, is_goal, cost

level = load_level("levels/level_01.json")
s0 = initial_state(level) # State xuất phát
is_goal(level, s) # True nếu khối ĐỨNG trên ô goal
get_successors(level, s) # [(Direction, State), ...] chỉ gồm nước đi hợp lệ
cost(level, s, direction, next_state) # chi phí 1 bước, hiện tại = 1
```

- Trạng thái goal là trạng thái kết thúc: `get_successors` trả về `[]`.
- Bình thường mỗi state có tối đa 4 successor; khi đang tách khối có tối đa 5 (4 hướng + `Direction.SWITCH`). Solver chỉ cần duyệt `get_successors`, không cần xử lý riêng split.
- `Direction.SWITCH` tính là một nước đi: nằm trong `path`, được đếm vào `solution_length`, và hiện có chi phí 1 như mọi nước (**TV3**: nếu đổi chi phí, heuristic A\* vẫn phải admissible với chi phí mới).
- **TV3 (A\*)**: heuristic phải xử lý được `state.is_split`. `h = 0` luôn admissible nên dùng được làm phương án dự phòng cho state tách khối.
- Mọi solver thống nhất chữ ký hàm: `solve(level) -> (path, stats)`
- `path`: `list[Direction]` (có thể chứa `Direction.SWITCH`) nếu tìm thấy lời giải, hoặc `None` nếu vô nghiệm.
- `stats`: `dict` chứa các thông số đo lường chuẩn:

```python
{
"time_ms": float, # Thời gian chạy (mili-giây, đo bằng time.perf_counter)
"memory_kb": float, # Bộ nhớ đỉnh (KB, đo bằng tracemalloc)
"expanded_nodes": int, # Số trạng thái đã lấy ra mở rộng
"solution_length": int, # Số bước đi (len(path), hoặc -1 nếu vô nghiệm)
"solution_cost": float, # Tổng chi phí lời giải (0.0 nếu vô nghiệm)
}
```

## 4. Hàm cho GUI / chơi tay

```python
from game import apply_move, MoveStatus, Direction
res = apply_move(level, s, Direction.UP)
res.status # OK | WIN | FALL_OFF_BOARD | FALL_VOID | FRAGILE_BREAK | BLOCKED
res.legal # True nếu OK hoặc WIN
res.fatal # True nếu THUA (rơi xuống / vỡ ô): GUI hiển thị thua và cho Restart
res.state # State mới (None nếu không hợp lệ)
res.events # tuple chuỗi: "switch", "split", "merge", "switch_control" (dùng cho hiệu ứng/âm thanh)
```

- `fatal = True` khi `status` là `FALL_OFF_BOARD`, `FALL_VOID` (gồm cả cầu đang đóng) hoặc `FRAGILE_BREAK`.
- `BLOCKED`: nước đi không thực hiện được nhưng không thua (ví dụ bấm `SWITCH` khi chưa tách khối). GUI bỏ qua nước đó, không hiện thua.
- Phím cách ánh xạ sang `Direction.SWITCH`. Vẽ hai khối nhỏ bằng `state.cells()`, đánh dấu khối đang điều khiển bằng `state.active_cell`.
- Ý nghĩa `events`: `"switch"` công tắc soft/heavy vừa kích hoạt; `"split"` khối vừa dịch chuyển và tách; `"merge"` hai khối nhỏ vừa ghép; `"switch_control"` vừa đổi khối điều khiển.

## 5. Định dạng file màn chơi (JSON)

```json
{
"name": "ten_man",
"grid": ["S.=###", "..=..#", "#.....", "###.G."],
"bridges": { "b1": { "cells": [[0,2],[1,2]], "open": false } },
  "switches": [
    { "pos": [r,c], "type": "soft|heavy", "targets": ["b1"], "mode": "toggle|open|close" },
    { "pos": [r,c], "type": "split", "cubes": [[r1,c1],[r2,c2]] }
  ]
}
```

| Ký tự           | Ô                                              |
| --------------- | ---------------------------------------------- |
| `.`             | sàn thường                                     |
| `#`             | ô trống (void)                                 |
| `S`             | xuất phát (là sàn, đúng 1 ô)                   |
| `G`             | goal (đúng 1 ô)                                |
| `F`             | fragile                                        |
| `=`             | cầu (phải thuộc đúng 1 bridge trong `bridges`) |
| `o` / `x` / `s` | công tắc soft / heavy / split                  |

- Thứ tự bit thứ `i` trong `state.bridges` tương ứng với thứ tự khai báo các key trong `"bridges"`.
- Mỗi ô công tắc (`o`, `x`, `s`) trong `grid` phải có đúng một khai báo trong `switches`; hai công tắc không được cùng một ô.
- Công tắc `soft`/`heavy` bắt buộc có `targets` (ít nhất một cầu có trong `bridges`). `mode` mặc định là `toggle`.
- `mode`: `toggle` = mỗi lần kích hoạt đảo trạng thái; `open`/`close` = đặt cố định (permanent).
- Split: `cubes` là vị trí hai khối sau khi tách, phải nằm trên ô không phải void, không trùng/kề nhau. Khối đầu tiên là khối điều khiển lúc đầu.
- Loader kiểm tra hợp lệ và ném `LevelError` nếu file sai.

## 6. Luật đã cài

- Nước đi bất hợp lệ nếu có ô ra ngoài bảng, ô void, cầu đóng, hoặc khối 1x1x2 đứng trên ô fragile.
- Nằm trên ô fragile / nằm ngang qua ô goal là hợp lệ.
- Thắng khi và chỉ khi khối 1x1x2 đứng trên ô goal. Khối nhỏ đi qua ô goal như sàn thường, không thắng.
- Kích hoạt công tắc: `soft` kích hoạt khi bất kỳ phần nào của khối hoặc khối nhỏ chạm vào; `heavy` và `split` chỉ kích hoạt khi khối 1x1x2 đứng (khối nhỏ không kích hoạt được).
- Mỗi nước lăn đều rời hết ô cũ nên một công tắc không bị kích hoạt hai lần liên tiếp mà không rời đi. Khối nằm đè hai công tắc thì cả hai cùng kích hoạt.
- Khi tách, khối dịch chuyển tới `cubes`; công tắc split không phát sinh thêm hiệu ứng nào khác. Hai khối nhỏ không chồng lên nhau, kề nhau là ghép ngay (ghép xong không kích hoạt lại công tắc). Soft kích hoạt trước rồi mới ghép nếu cả hai xảy ra cùng một nước.
- Chỉ khối 1x1x2 đứng mới làm vỡ ô fragile; khối nhỏ đứng được trên ô fragile (đổi bằng `CUBE_BREAKS_FRAGILE` trong `engine.py`).
- Nếu công tắc vừa kích hoạt đóng cầu mà khối (hoặc khối nhỏ còn lại) đang đứng trên cầu đó thì rơi (`FALL_VOID`).
- Đổi khối điều khiển (`Direction.SWITCH`) luôn hợp lệ khi đang tách khối.
