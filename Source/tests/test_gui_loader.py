import unittest

from gui.level_loader import load_levels


class GuiLevelLoader(unittest.TestCase):
    def test_loads_levels_with_fragile_tiles(self):
        levels = load_levels()
        self.assertEqual(levels["level_05"]["grid"][0][3], "f")


if __name__ == "__main__":
    unittest.main()
