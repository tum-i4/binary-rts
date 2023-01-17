import os
import unittest
from pathlib import Path
from typing import Optional, Set

from typer.testing import CliRunner

from binaryrts.commands.utils import (
    app,
)
from binaryrts.parser.coverage import TEST_ID_SEP
from binaryrts.util.fs import temp_path


class CliUtilsMergeTestCase(unittest.TestCase):
    runner: Optional[CliRunner] = None

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.runner = CliRunner()

    def test_merge_excludes(self):
        with temp_path() as tmp_dir:
            tc1 = f"foo.module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}TEST_F(foo)"
            tc2 = f"foo.module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}TEST_F(bar)"
            tc3 = f"foo.module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}TEST_F(baz)"
            excludes1 = Path(tmp_dir) / "excludes1.txt"
            excludes1.write_text("\n".join([tc1, tc2]))
            excludes2 = Path(tmp_dir) / "excludes2.txt"
            excludes2.write_text(tc3)
            result = self.runner.invoke(
                app,
                [
                    "merge",
                    "-o",
                    tmp_dir,
                    "--exclude",
                    excludes1.__str__(),
                    "--exclude",
                    excludes2.__str__(),
                ],
                catch_exceptions=True,
            )
            self.assertEqual(result.exit_code, 0)
            self.assertTrue((Path(tmp_dir) / "excluded.txt").exists())
            expected_tests: Set[str] = {tc1, tc2, tc3}
            actual_tests: Set[str] = {
                line.strip()
                for line in (Path(tmp_dir) / "excluded.txt").read_text().splitlines()
            }
            self.assertSetEqual(expected_tests, actual_tests)
        self.assertFalse(os.path.exists(tmp_dir))

    def test_merge_exclude_include(self):
        with temp_path() as tmp_dir:
            tc1 = f"foo.module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}TEST_F(foo)"
            tc2 = f"foo.module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}TEST_F(bar)"
            tc3 = f"foo.module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}TEST_F(baz)"
            tc4 = f"foo.module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}TEST_F(foobar)"
            excludes1 = Path(tmp_dir) / "excludes1.txt"
            excludes1.write_text("\n".join([tc1, tc2, tc3]))
            includes_2 = Path(tmp_dir) / "includes2.txt"
            includes_2.write_text("\n".join([tc3, tc4]))
            result = self.runner.invoke(
                app,
                [
                    "merge",
                    "-o",
                    tmp_dir,
                    "--exclude",
                    excludes1.__str__(),
                    "--include",
                    includes_2.__str__(),
                ],
                catch_exceptions=True,
            )
            self.assertEqual(result.exit_code, 0)
            self.assertTrue((Path(tmp_dir) / "excluded.txt").exists())
            expected_tests: Set[str] = {tc1, tc2}
            actual_tests: Set[str] = {
                line.strip()
                for line in (Path(tmp_dir) / "excluded.txt").read_text().splitlines()
            }
            self.assertSetEqual(expected_tests, actual_tests)
        self.assertFalse(os.path.exists(tmp_dir))


if __name__ == "__main__":
    unittest.main()
