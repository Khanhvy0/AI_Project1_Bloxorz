# Engin

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
