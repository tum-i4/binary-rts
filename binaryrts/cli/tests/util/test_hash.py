import os
import unittest
from pathlib import Path

from binaryrts.util.hash import hash_file, hash_string

RESOURCES_DIR: Path = Path(os.path.dirname(__file__)) / "resources"


class HashUtilTestCase(unittest.TestCase):
    def test_sha256_file(self):
        first_hash: str = hash_file(file_path=(RESOURCES_DIR / "main.cpp"))
        second_hash: str = hash_file(file_path=(RESOURCES_DIR / "main.cpp"))
        self.assertEqual(first_hash, second_hash)

    def test_sha256_string(self):
        first_hash: str = hash_string(string="int main()\n{\n\treturn 0;\n}")
        second_hash: str = hash_string(string="int main()\n{\n\treturn 0;\n}")
        self.assertEqual(first_hash, second_hash)


if __name__ == "__main__":
    unittest.main()
