import os
import unittest
from pathlib import Path

from binaryrts.util.fs import temp_file, temp_path, get_parent


class FileSystemUtilTestCase(unittest.TestCase):
    def test_temp_file(self):
        file_path: Path
        with temp_file() as file:
            file_path = file
            self.assertTrue(file_path.exists())
            self.assertTrue(file_path.is_file())
        self.assertFalse(file_path.exists())
        self.assertFalse(file_path.is_file())

    def test_temp_path(self):
        file_path: Path
        with temp_path() as directory:
            dir_path = Path(directory).resolve()
            self.assertTrue(dir_path.exists())
            self.assertTrue(dir_path.is_dir())
            self.assertEqual(Path(os.getcwd()).resolve(), dir_path)
        self.assertFalse(dir_path.exists())
        self.assertFalse(dir_path.is_file())

    def test_temp_path_without_change_dir(self):
        file_path: Path
        with temp_path(change_dir=False) as directory:
            dir_path = Path(directory).absolute()
            self.assertTrue(dir_path.exists())
            self.assertTrue(dir_path.is_dir())
            self.assertNotEqual(Path(os.getcwd()).resolve(), dir_path)
        self.assertFalse(dir_path.exists())
        self.assertFalse(dir_path.is_file())

    def test_get_parent(self):
        self.assertEqual(Path("/a/b/c"), get_parent(Path("/a/b/c/d.txt"), depth=1))
        self.assertEqual(Path("/a/b"), get_parent(Path("/a/b/c/d.txt"), depth=2))
        self.assertEqual(Path("/a"), get_parent(Path("/a/b/c/d.txt"), depth=3))
        self.assertEqual(Path("/"), get_parent(Path("/a/b/c/d.txt"), depth=4))
        self.assertEqual(Path("/"), get_parent(Path("/a/b/c/d.txt"), depth=5))


if __name__ == "__main__":
    unittest.main()
