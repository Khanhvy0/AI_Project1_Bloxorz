import unittest
from game import State, Orient, Direction, MOVES, TRANSITIONS

O, D = Orient, Direction


def roll(state, d):
    no, dr, dc = TRANSITIONS[(state.orient, d)]
    return State(state.r + dr, state.c + dc, no)


class TransitionTable(unittest.TestCase):
    def test_table_complete(self):
        self.assertEqual(len(TRANSITIONS), 12)
        for o in O:
            for d in MOVES:
                self.assertIn((o, d), TRANSITIONS)

    def test_standing_cells(self):
        s = State(5, 5, O.STAND)
        self.assertEqual(roll(s, D.UP).cells(), ((3, 5), (4, 5)))
        self.assertEqual(roll(s, D.DOWN).cells(), ((6, 5), (7, 5)))
        self.assertEqual(roll(s, D.LEFT).cells(), ((5, 3), (5, 4)))
        self.assertEqual(roll(s, D.RIGHT).cells(), ((5, 6), (5, 7)))

    def test_horizontal(self):
        s = State(5, 5, O.HORIZ)  # chiếm (5,5),(5,6)
        self.assertEqual(roll(s, D.LEFT), State(5, 4, O.STAND))
        self.assertEqual(roll(s, D.RIGHT), State(5, 7, O.STAND))
        self.assertEqual(roll(s, D.UP).cells(), ((4, 5), (4, 6)))
        self.assertEqual(roll(s, D.DOWN).cells(), ((6, 5), (6, 6)))

    def test_vertical(self):
        s = State(5, 5, O.VERT)  # chiếm (5,5),(6,5)
        self.assertEqual(roll(s, D.UP), State(4, 5, O.STAND))
        self.assertEqual(roll(s, D.DOWN), State(7, 5, O.STAND))
        self.assertEqual(roll(s, D.LEFT).cells(), ((5, 4), (6, 4)))
        self.assertEqual(roll(s, D.RIGHT).cells(), ((5, 6), (6, 6)))

    def test_orientation_changes(self):
        expected = {
            (O.STAND, D.UP): O.VERT, (O.STAND, D.DOWN): O.VERT,
            (O.STAND, D.LEFT): O.HORIZ, (O.STAND, D.RIGHT): O.HORIZ,
            (O.HORIZ, D.LEFT): O.STAND, (O.HORIZ, D.RIGHT): O.STAND,
            (O.HORIZ, D.UP): O.HORIZ, (O.HORIZ, D.DOWN): O.HORIZ,
            (O.VERT, D.UP): O.STAND, (O.VERT, D.DOWN): O.STAND,
            (O.VERT, D.LEFT): O.VERT, (O.VERT, D.RIGHT): O.VERT,
        }
        for key, o in expected.items():
            self.assertEqual(TRANSITIONS[key][0], o, key)

    def test_reversibility(self):
        """Lăn rồi lăn ngược lại phải về đúng trạng thái cũ (tính chất vật lý của khối)."""
        for o in O:
            s = State(10, 10, o)
            for d in MOVES:
                self.assertEqual(roll(roll(s, d), d.opposite), s, (o, d))

    def test_cells_count(self):
        self.assertEqual(len(State(0, 0, O.STAND).cells()), 1)
        self.assertEqual(len(State(0, 0, O.HORIZ).cells()), 2)
        self.assertEqual(len(State(0, 0, O.VERT).cells()), 2)

    def test_hashable(self):
        self.assertEqual(len({State(1, 1, O.STAND), State(1, 1, O.STAND)}), 1)
        self.assertNotEqual(State(1, 1, O.STAND, 0), State(1, 1, O.STAND, 1))


if __name__ == "__main__":
    unittest.main()
