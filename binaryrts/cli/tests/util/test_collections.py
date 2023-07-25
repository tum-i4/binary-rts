import unittest

from binaryrts.util.collections import array_split


class CollectionsTestCase(unittest.TestCase):
    def test_array_split(self):
        self.assertEqual([[1, 2], [3, 4], [5]],
                         array_split(list(range(1, 6)), 3))
        self.assertEqual([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12], [13, 14], [15, 16], [17, 18]],
                         array_split(list(range(1, 19)), 7))
        self.assertEqual([[1], [2], [3]],
                         array_split(list(range(1, 4)), 3))
        self.assertEqual([[1], [2], [3], [], []],
                         array_split(list(range(1, 4)), 5))
        self.assertEqual([[1, 2, 3, 4]],
                         array_split(list(range(1, 5)), 1))
        self.assertEqual([[1, 2, 3, 4]],
                         array_split(list(range(1, 5)), 0))


if __name__ == "__main__":
    unittest.main()
