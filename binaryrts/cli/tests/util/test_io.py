import os
import unittest
from pathlib import Path
from typing import List

from binaryrts.util.io import slice_file_into_chunks

RESOURCES_DIR: Path = Path(os.path.dirname(__file__)) / "resources"


class IOUtilTestCase(unittest.TestCase):
    def test_slice_file_into_chunks(self):
        expected: List[str] = [
            "#define MAX(a,b) a>b?a:b\n",
            "int main()\n{\n\treturn 0;\n}",
        ]
        actual: List[str] = slice_file_into_chunks(
            RESOURCES_DIR / "main.cpp", [(1, 1), (11, 8)]
        )
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
