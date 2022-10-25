import json
import os
import shutil
import unittest
from pathlib import Path
from typing import Optional, Dict, List, Set

from typer.testing import CliRunner

from binaryrts.commands.select import (
    app,
    EXCLUDED_TESTS_FILE,
    INCLUDED_TESTS_FILE,
    SELECTION_CAUSES_FILE,
)
from binaryrts.parser.coverage import (
    TestFunctionTraces,
    FunctionLookupTable,
    CoveredFunction,
    TEST_ID_SEP,
    PICKLE_FUNCTION_LOOKUP_FILE,
    FUNCTION_LOOKUP_FILE,
    TEST_FUNCTION_TRACES_FILE,
    PICKLE_TEST_FUNCTION_TRACES_FILE,
)
from binaryrts.vcs.git import temp_clone, temp_repo, GitClient

RESOURCES_DIR: Path = Path(os.path.dirname(__file__)) / "resources"
OUTPUT_DIR: Path = RESOURCES_DIR / "output"
SAMPLE_MODULE_DIR: Path = RESOURCES_DIR / "sample_module"
FUNCTION_LOOKUP_TABLE: Path = OUTPUT_DIR / FUNCTION_LOOKUP_FILE
PICKLE_FUNCTION_LOOKUP_TABLE: Path = OUTPUT_DIR / PICKLE_FUNCTION_LOOKUP_FILE
TEST_FUNCTION_TRACES: Path = OUTPUT_DIR / TEST_FUNCTION_TRACES_FILE
PICKLE_TEST_FUNCTION_TRACES: Path = OUTPUT_DIR / PICKLE_TEST_FUNCTION_TRACES_FILE


class CliSelectTestCase(unittest.TestCase):
    runner: Optional[CliRunner] = None

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.runner = CliRunner()

    def setUp(self) -> None:
        super().setUp()

    def test_select_cpp(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)
                shutil.copytree(
                    src=SAMPLE_MODULE_DIR / "src",
                    dst=git_client.root / "src",
                    dirs_exist_ok=False,
                )
                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Initial Commit")
                git_client.git_repo.git.push()
                target_branch: str = git_client.git_repo.active_branch.name

                function_lookup_table: Dict[str, List[CoveredFunction]] = {
                    f"src{os.sep}test.h": [
                        CoveredFunction(
                            0,
                            f"src{os.sep}test.h",
                            "Max(int,int)",
                            5,
                            7,
                            None,
                            None,
                            None,
                        ),
                        CoveredFunction(
                            1,
                            f"src{os.sep}test.h",
                            "TEST(FooSuite,Max)",
                            9,
                            11,
                            None,
                            None,
                            None,
                        ),
                    ]
                }

                FunctionLookupTable(table=function_lookup_table).to_csv(
                    FUNCTION_LOOKUP_TABLE
                )
                test_function_traces: Dict[str, Set[int]] = {
                    f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max": {0, 1}
                }
                TestFunctionTraces(table=test_function_traces).to_csv(
                    TEST_FUNCTION_TRACES
                )

                # modifying change
                git_client.git_repo.git.checkout(b="feature/modify")
                file = Path("src") / "test.h"
                file.write_text(
                    file.read_text().replace(
                        "return a > b", "int c = 0; \nreturn a > b"
                    )
                )
                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Change Max")

                result = self.runner.invoke(
                    app,
                    [
                        "-o",
                        OUTPUT_DIR.__str__(),
                        "--from",
                        target_branch,
                        "--to",
                        "HEAD",
                        "cpp",
                        "--lookup",
                        FUNCTION_LOOKUP_TABLE,
                        "--traces",
                        TEST_FUNCTION_TRACES,
                    ],
                    catch_exceptions=True,
                )
                self.assertEqual(result.exit_code, 0, msg=result.stdout)
                self.assertTrue((OUTPUT_DIR / INCLUDED_TESTS_FILE).exists())
                self.assertTrue(
                    (OUTPUT_DIR / INCLUDED_TESTS_FILE).read_text()
                    == f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max"
                )
                self.assertTrue((OUTPUT_DIR / EXCLUDED_TESTS_FILE).exists())
                self.assertTrue((OUTPUT_DIR / EXCLUDED_TESTS_FILE).read_text() == "")
                self.assertTrue((OUTPUT_DIR / SELECTION_CAUSES_FILE).exists())
                causes: Dict[str, List[str]] = json.load(
                    (OUTPUT_DIR / SELECTION_CAUSES_FILE).open("r")
                )
                self.assertDictEqual(
                    causes,
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max": [
                            f"src{os.sep}test.h::::::Max(int,int)"
                        ]
                    },
                )

    def test_select_cpp_evaluation(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)
                shutil.copytree(
                    src=SAMPLE_MODULE_DIR / "src",
                    dst=git_client.root / "src",
                    dirs_exist_ok=False,
                )
                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Initial Commit")
                git_client.git_repo.git.push()
                target_branch: str = git_client.git_repo.active_branch.name

                function_lookup_table: Dict[str, List[CoveredFunction]] = {
                    f"src{os.sep}test.h": [
                        CoveredFunction(
                            0,
                            f"src{os.sep}test.h",
                            "Max(int,int)",
                            5,
                            7,
                            None,
                            None,
                            None,
                        ),
                        CoveredFunction(
                            1,
                            f"src{os.sep}test.h",
                            "TEST(FooSuite,Max)",
                            9,
                            11,
                            None,
                            None,
                            None,
                        ),
                    ]
                }

                FunctionLookupTable(table=function_lookup_table).to_csv(
                    FUNCTION_LOOKUP_TABLE
                )
                test_function_traces: Dict[str, Set[int]] = {
                    f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max": {0, 1}
                }
                TestFunctionTraces(table=test_function_traces).to_csv(
                    TEST_FUNCTION_TRACES
                )

                # modifying change
                git_client.git_repo.git.checkout(b="feature/modify")
                file = Path("src") / "test.h"
                file.write_text(
                    file.read_text().replace(
                        "return a > b", "int c = 0; \nreturn a > b"
                    )
                )
                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Change Max")

                result = self.runner.invoke(
                    app,
                    [
                        "-o",
                        OUTPUT_DIR.__str__(),
                        "--from",
                        target_branch,
                        "--to",
                        "HEAD",
                        "cpp",
                        "--lookup",
                        FUNCTION_LOOKUP_TABLE,
                        "--traces",
                        TEST_FUNCTION_TRACES,
                        "--evaluation",
                    ],
                    catch_exceptions=True,
                )
                self.assertEqual(result.exit_code, 0, msg=result.stdout)

    def test_select_cpp_pickle_input(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)
                shutil.copytree(
                    src=SAMPLE_MODULE_DIR / "src",
                    dst=git_client.root / "src",
                    dirs_exist_ok=False,
                )
                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Initial Commit")
                git_client.git_repo.git.push()
                target_branch: str = git_client.git_repo.active_branch.name

                function_lookup_table: Dict[str, List[CoveredFunction]] = {
                    f"src{os.sep}test.h": [
                        CoveredFunction(
                            0,
                            f"src{os.sep}test.h",
                            "Max(int,int)",
                            5,
                            7,
                            None,
                            None,
                            None,
                        ),
                        CoveredFunction(
                            1,
                            f"src{os.sep}test.h",
                            "TEST(FooSuite,Max)",
                            9,
                            11,
                            None,
                            None,
                            None,
                        ),
                    ]
                }

                FunctionLookupTable(table=function_lookup_table).to_pickle(
                    PICKLE_FUNCTION_LOOKUP_TABLE
                )
                test_function_traces: Dict[str, Set[int]] = {
                    f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max": {0, 1}
                }
                TestFunctionTraces(table=test_function_traces).to_pickle(
                    PICKLE_TEST_FUNCTION_TRACES
                )

                # modifying change
                git_client.git_repo.git.checkout(b="feature/modify")
                file = Path("src") / "test.h"
                file.write_text(
                    file.read_text().replace(
                        "return a > b", "int c = 0; \nreturn a > b"
                    )
                )
                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Change Max")

                result = self.runner.invoke(
                    app,
                    [
                        "-o",
                        OUTPUT_DIR.__str__(),
                        "--from",
                        target_branch,
                        "--to",
                        "HEAD",
                        "cpp",
                        "--lookup",
                        PICKLE_FUNCTION_LOOKUP_TABLE,
                        "--traces",
                        PICKLE_TEST_FUNCTION_TRACES,
                    ],
                    catch_exceptions=True,
                )
                self.assertEqual(result.exit_code, 0, msg=result.stdout)


if __name__ == "__main__":
    unittest.main()
