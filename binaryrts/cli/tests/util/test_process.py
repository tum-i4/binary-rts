import platform
import unittest

from binaryrts.util.process import check_executable_exists


class OSExecUtilTestCase(unittest.TestCase):
    def test_check_executable(self):
        if platform.system() != "Windows":
            self.assertEqual("/bin/ls", check_executable_exists("ls"))
            self.assertIsNone(check_executable_exists("some-non-existing-executable"))


if __name__ == "__main__":
    unittest.main()
