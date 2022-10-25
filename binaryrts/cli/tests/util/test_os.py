import platform
import unittest

from binaryrts.util.os import os_is_windows, get_os, OSPlatform


class OSPlatformUtilTestCase(unittest.TestCase):
    def test_platform_is_windows(self):
        if platform.system() == "Windows":
            self.assertTrue(os_is_windows())
        else:
            self.assertFalse(os_is_windows())

    def test_get_os(self):
        returned_os = get_os()
        if platform.system() == "Darwin":
            self.assertEqual(returned_os, OSPlatform.DARWIN)
        elif platform.system() == "Linux":
            self.assertEqual(returned_os, OSPlatform.LINUX)
        elif platform.system() == "Windows":
            self.assertEqual(returned_os, OSPlatform.WINDOWS)


if __name__ == "__main__":
    unittest.main()
