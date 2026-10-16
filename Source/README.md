# Engin

```
game/      state.py (State, bảng chuyển hướng) | level.py (loader JSON) | engine.py (luật chơi)
levels/    các màn chơi mẫu (.json)
tests/     unit test
docs/      INTERFACE.md (đặc tả cho cả nhóm)
```

```bash

# Chạy riêng một file test
python -m unittest tests.test_transitions -v
python -m unittest tests.test_levels -v

# Chạy toàn bộ test:
python -m unittest discover -s tests -t . -v
```
