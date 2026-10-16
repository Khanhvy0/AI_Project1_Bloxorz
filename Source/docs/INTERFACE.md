# Đặc tả interface Engine

> Các thành viên khác chỉ cần `from game import ...`.

## 1. Quy ước

- Toạ độ `(r, c)` = (hàng, cột), gốc ở góc trên-trái, `r` tăng xuống dưới.
- `Direction`: `UP, DOWN, LEFT, RIGHT`. `Orient`: `STAND, HORIZ, VERT`.
- Ô neo `(r, c)` của khối = ô trên-trái: STAND {(r,c)}, HORIZ {(r,c),(r,c+1)}, VERT {(r,c),(r+1,c)}.

## 2. State & Level

### 2.1. `State` (bất biến, hashable, comparable)

| Trường            | Ý nghĩa                                             |
| ----------------- | --------------------------------------------------- |
| `r, c`            | ô neo                                               |
| `orient`          | hướng khối (`Orient`)                               |
| `bridges`         | bitmask: bit `i = 1` nếu cầu thứ `i` đang mở        |
| `split`, `active` | dành cho split switch (Tuần 2), hiện là `None`, `0` |

- `state.cells()` trả về tuple các ô `(r, c)` khối đang chiếm.
- Dùng `State` trực tiếp làm key của `set`/`dict`, và có hỗ trợ so sánh thứ tự (`order=True` / `__lt__`) để đẩy trực tiếp tuple `(cost, state)` vào `heapq` trong UCS / A\*.

### 2.2. `Level` (thông tin màn chơi)

| Thuộc tính / Phương thức        | Ý nghĩa                                                              |
| ------------------------------- | -------------------------------------------------------------------- |
| `level.name`                    | tên màn chơi (`str`)                                                 |
| `level.rows`, `level.cols`      | kích thước bảng (`int`)                                              |
| `level.start`                   | toạ độ `(r, c)` ô xuất phát                                          |
| `level.goal`                    | toạ độ `(r, c)` ô đích (dùng tính heuristic cho A\*)                 |
| `level.tile_at(r, c)`           | trả về ký tự loại ô tại `(r, c)` (`.`, `#`, `S`, `G`, `F`, `=`, ...) |
| `level.is_bridge_open(s, r, c)` | trả về `True` nếu ô cầu tại `(r, c)` đang mở ứng với trạng thái `s`  |

## 3. Hàm cho solver

```python
from game import load_level, initial_state, get_successors, is_goal, cost

level = load_level("levels/level_01.json")
s0 = initial_state(level) # State xuất phát
is_goal(level, s) # True nếu khối ĐỨNG trên ô goal
get_successors(level, s) # [(Direction, State), ...] chỉ gồm nước đi hợp lệ
cost(level, s, direction, next_state) # chi phí 1 bước (hiện = 1, TV3 định nghĩa lại)
```

- Trạng thái goal là trạng thái kết thúc: `get_successors` trả về `[]`.
- Mọi solver thống nhất chữ ký hàm: `solve(level) -> (path, stats)`
- `path`: `list[Direction]` nếu tìm thấy lời giải, hoặc `None` nếu vô nghiệm.
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
from game import apply_move, MoveStatus
res = apply_move(level, s, Direction.UP)
res.status # OK | WIN | FALL_OFF_BOARD | FALL_VOID | FRAGILE_BREAK
res.legal # True nếu OK hoặc WIN
res.state # State mới (None nếu thua)
```

Nếu `res.legal` là `False` thì GUI hiển thị thua và cho Restart. `FALL_VOID` gồm cả cầu đang đóng.

## 5. Định dạng file màn chơi (JSON)

```json
{
"name": "ten_man",
"grid": ["S.=###", "..=..#", "#.....", "###.G."],
"bridges": { "b1": { "cells": [[0,2],[1,2]], "open": false } },
"switches": [ { "pos": [r,c], "type": "soft|heavy|split",
"targets": ["b1"], "mode": "toggle|open|close" } ]
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
- `mode`: `toggle` = mỗi lần kích hoạt đảo trạng thái; `open`/`close` = đặt cố định (permanent).
- Switch `split` có thêm `"cubes": [[r1,c1],[r2,c2]]` (vị trí hai khối sau khi tách) - Tuần 2.
- Loader kiểm tra hợp lệ và ném `LevelError` nếu file sai.

## 6. Luật đã cài (Tuần 1)

- Nước đi bất hợp lệ nếu có ô ra ngoài bảng, ô void, cầu đóng, hoặc đứng trên ô fragile.
- Nằm trên ô fragile / nằm ngang qua ô goal là hợp lệ.
- Thắng khi và chỉ khi khối đứng trên ô goal.

## 7. Chưa làm (Tuần 2)

Kích hoạt soft/heavy/split switch (`_apply_switches` trong `engine.py`), toggle/permanent, tách và ghép khối.
