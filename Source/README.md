# Engin

## Chạy game

Mở terminal tại thư mục `Source`, cài Flask nếu chưa có rồi chạy:

```bash
pip install -r requirements.txt
python main.py
```

Mở http://127.0.0.1:5000 trên trình duyệt để chơi. Nhấn `Ctrl+C` trong terminal để dừng.

## Chạy test

```bash
python -m unittest discover -s tests -t . -v
```

## Cấu trúc

```
game/      state.py (State, bảng chuyển hướng) | level.py (loader JSON) | engine.py (luật chơi)
levels/    các màn chơi mẫu (.json)
tests/     unit test
docs/      INTERFACE.md (đặc tả cho cả nhóm)
```

## Cách chạy
```bash
# Tạo môi trường ảo( .venv) để cô lập chương trình
python -m venv .venv
# Sử dụng môi trường ảo
# Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate

# Chạy riêng một file test
python -m unittest tests.test_transitions -v
python -m unittest tests.test_levels -v

# Chạy toàn bộ test:
python -m unittest discover -s tests -t . -v
```
