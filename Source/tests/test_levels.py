"""Kiểm tra mọi file trong levels/ (kịch bản test theo nhóm độ khó)."""
import glob, os, unittest
from dataclasses import replace
from game import load_level, initial_state, State
import game.engine as engine
from tests.helpers import bfs_path_length

LEVEL_DIR = os.path.join(os.path.dirname(__file__), "..", "levels")
FILES = sorted(glob.glob(os.path.join(LEVEL_DIR, "*.json")))

# Đổi thành True khi _apply_switches (Tuần 2) đã làm xong
SWITCH_LOGIC_READY = False


def has_switches(level):
    return bool(level.switches)


class LevelFiles(unittest.TestCase):
    def test_files_exist(self):
        self.assertGreaterEqual(len(FILES), 1)

    def test_load_ok(self):
        """Mọi file phải đọc được (đúng định dạng, hàng đều nhau, có S và G...)."""
        for f in FILES:
            with self.subTest(level=os.path.basename(f)):
                load_level(f)

    def test_goal_reachable_if_all_bridges_open(self):
        """Kiểm tra BỐ CỤC: nếu mọi cầu đều mở thì goal phải tới được.
        Bắt lỗi 'đảo goal bị cô lập' mà không cần logic công tắc."""
        for f in FILES:
            with self.subTest(level=os.path.basename(f)):
                lv = load_level(f)
                lv.initial_bridges = (1 << len(lv.bridge_ids)) - 1
                self.assertIsNotNone(bfs_path_length(lv), "goal không tới được dù mọi cầu mở")

    def test_solvable_without_switches(self):
        """Màn không có công tắc (nhóm 1, 2) phải giải được ngay."""
        for f in FILES:
            lv = load_level(f)
            if has_switches(lv):
                continue
            with self.subTest(level=os.path.basename(f)):
                self.assertIsNotNone(bfs_path_length(lv))

    @unittest.skipUnless(SWITCH_LOGIC_READY, "chờ logic công tắc (Tuần 2)")
    def test_solvable_with_switches(self):
        for f in FILES:
            lv = load_level(f)
            if not has_switches(lv):
                continue
            with self.subTest(level=os.path.basename(f)):
                self.assertIsNotNone(bfs_path_length(lv))


if __name__ == "__main__":
    unittest.main()
