import os.path
import shutil
import unittest
from pathlib import Path
from typing import Tuple, List, Dict, Set

from binaryrts.parser.coverage import (
    FunctionLookupTable,
    TestFunctionTraces,
    CoveredFunction,
    TEST_ID_SEP,
)
from binaryrts.parser.sourcecode import FunctionDefinition
from binaryrts.rts.base import SelectionCause
from binaryrts.rts.cpp import CppFunctionLevelRTS, CppFileLevelRTS
from binaryrts.vcs.git import temp_repo, temp_clone, GitClient

RESOURCES_DIR: Path = Path(os.path.dirname(__file__)) / "resources"
SAMPLE_MODULE_DIR: Path = RESOURCES_DIR / "sample_module"


def setup_repo_init_lookup_traces(
    git_client: GitClient,
) -> Tuple[FunctionLookupTable, TestFunctionTraces]:
    # create initial commit on main branch
    shutil.copytree(
        src=SAMPLE_MODULE_DIR / "src",
        dst=git_client.root / "src",
        dirs_exist_ok=False,
    )
    git_client.git_repo.git.add(".")
    git_client.git_repo.git.commit(message="Initial Commit")
    git_client.git_repo.git.push()

    # create lookup and traces
    function_lookup_table: Dict[str, List[CoveredFunction]] = {
        f"src{os.sep}foo.h": [
            CoveredFunction(
                0, f"src{os.sep}foo.h", "Maximum(int,int)", 3, 5, None, None, "Foo"
            ),
            CoveredFunction(
                1, f"src{os.sep}foo.h", "Max(int,int)", 8, 10, None, None, None
            ),
        ],
        f"src{os.sep}test.cpp": [
            CoveredFunction(
                2,
                f"src{os.sep}test.cpp",
                "TEST_F(FooSuite,FooMax)",
                4,
                7,
                None,
                None,
                None,
            ),
            CoveredFunction(
                3,
                f"src{os.sep}test.cpp",
                "TEST_F(FooSuite,Max)",
                9,
                11,
                None,
                None,
                None,
            ),
            CoveredFunction(
                4,
                f"src{os.sep}test.cpp",
                "TEST_F(FooSuite,MaxMacro)",
                13,
                15,
                None,
                None,
                None,
            ),
        ],
        f"src{os.sep}test.h": [
            CoveredFunction(
                5,
                f"src{os.sep}test.h",
                "SetUpTestSuite()",
                8,
                10,
                "static",
                None,
                "FooSuite",
            )
        ],
    }
    test_function_traces: Dict[str, Set[int]] = {
        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}*": {5},
        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax": {
            0,
            2,
        },
        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max": {
            1,
            3,
        },
        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}MaxMacro": {4},
    }
    return FunctionLookupTable(table=function_lookup_table), TestFunctionTraces(
        table=test_function_traces
    )


class CppFileLevelRTSTestCase(unittest.TestCase):
    def test_selection_modification(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                (
                    function_lookup_table,
                    test_function_traces,
                ) = setup_repo_init_lookup_traces(git_client=git_client)

                # set up RTS algo
                algo: CppFileLevelRTS = CppFileLevelRTS(
                    git_client=git_client,
                    function_lookup_table=function_lookup_table,
                    test_function_traces=test_function_traces,
                    output_dir=git_client.root,
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                file = Path("src") / "foo.h"
                file.write_text(
                    file.read_text().replace(
                        "return a > b", "int c = 0; \nreturn a > b"
                    )
                )

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Change Foo::Maximum")

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max",
                    },
                    included_tests,
                )
                self.assertSetEqual(
                    {f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}MaxMacro"},
                    excluded_tests,
                )
                self.assertDictEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax": [
                            f"src{os.sep}foo.h"
                        ],
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max": [
                            f"src{os.sep}foo.h"
                        ],
                    },
                    selection_causes,
                )


class CppFunctionLevelRTSTestCase(unittest.TestCase):
    def test_get_ids_of_changed_functions(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                # set up git client
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)
                function_lookup_table: Dict[str, List[CoveredFunction]] = {
                    "/some/file/math.cpp": [
                        CoveredFunction(
                            0,  # "identifier",
                            "/some/file/math.cpp",  # "file",
                            "max(int)",  # "function",
                            2,  # "start",
                            5,  # "end",
                            None,  # "properties",
                            None,  # "namespace",
                            "Math",  # "class_name",
                        )
                    ]
                }
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=FunctionLookupTable(
                        table=function_lookup_table
                    ),
                    test_function_traces=TestFunctionTraces(),
                    output_dir=local_repo,
                )
                self.assertEqual(
                    algo._get_ids_of_affected_functions_for_file(
                        [
                            FunctionDefinition(
                                file=Path("/some/file/math.cpp"),
                                signature="max(int)",
                                start_line=2,
                                end_line=5,
                                namespace=None,
                                class_name="Math",
                                properties=None,
                            )
                        ],
                        file=None,
                    ),
                    {0},
                )
                self.assertEqual(
                    algo._get_ids_of_affected_functions_for_file(
                        [
                            FunctionDefinition(
                                file=Path("/some/file/math.cpp"),
                                signature="min(int)",
                                start_line=2,
                                end_line=5,
                                namespace=None,
                                class_name="Math",
                                properties=None,
                            )
                        ],
                        file=None,
                    ),
                    set(),
                )

    def test_selection_modification(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                (
                    function_lookup_table,
                    test_function_traces,
                ) = setup_repo_init_lookup_traces(git_client=git_client)

                # set up RTS algo
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=function_lookup_table,
                    test_function_traces=test_function_traces,
                    output_dir=git_client.root,
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                file = Path("src") / "foo.h"
                file.write_text(
                    file.read_text().replace(
                        "return a > b", "int c = 0; \nreturn a > b"
                    )
                )

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Change Foo::Maximum")

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(
                    {f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax"},
                    included_tests,
                )
                self.assertSetEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}MaxMacro",
                    },
                    excluded_tests,
                )
                self.assertDictEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax": [
                            f"src{os.sep}foo.h::::Foo::Maximum(int,int)"
                        ]
                    },
                    selection_causes,
                )

    def test_selection_with_includes(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                (
                    function_lookup_table,
                    test_function_traces,
                ) = setup_repo_init_lookup_traces(git_client=git_client)

                # set up RTS algo
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=function_lookup_table,
                    test_function_traces=test_function_traces,
                    output_dir=git_client.root,
                    includes_regex=".*inc.*",
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                file = Path("src") / "foo.h"
                file.write_text(
                    file.read_text().replace(
                        "return a > b", "int c = 0; \nreturn a > b"
                    )
                )

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(
                    message="Change Foo::Maximum in not included file"
                )

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(
                    set(),
                    included_tests,
                )
                self.assertSetEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}MaxMacro",
                    },
                    excluded_tests,
                )
                self.assertDictEqual(
                    dict(),
                    selection_causes,
                )

    def test_selection_with_excludes(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                (
                    function_lookup_table,
                    test_function_traces,
                ) = setup_repo_init_lookup_traces(git_client=git_client)

                # set up RTS algo
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=function_lookup_table,
                    test_function_traces=test_function_traces,
                    output_dir=git_client.root,
                    excludes_regex=".*",
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                file = Path("src") / "foo.h"
                file.write_text(
                    file.read_text().replace(
                        "return a > b", "int c = 0; \nreturn a > b"
                    )
                )

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(
                    message="Change Foo::Maximum in excluded file"
                )

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(
                    set(),
                    included_tests,
                )
                self.assertSetEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}MaxMacro",
                    },
                    excluded_tests,
                )
                self.assertDictEqual(
                    dict(),
                    selection_causes,
                )

    def test_selection_add_file(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                (
                    function_lookup_table,
                    test_function_traces,
                ) = setup_repo_init_lookup_traces(git_client=git_client)

                # set up RTS algo
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=function_lookup_table,
                    test_function_traces=test_function_traces,
                    output_dir=git_client.root,
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                branch: str = "feature/xxx"
                git_client.git_repo.git.checkout(b=branch)

                file = Path("src") / "bar.h"
                file.write_text(
                    """
class Foo {
public:
	int Maximum(int a, int b) {
		return a > b ? a : b;
	}
};

int Max(int c, int d) {
	return c > d ? c : d;
}
"""
                )
                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Add new version of foo.h")

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision=branch
                )
                self.assertSetEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max",
                    },
                    included_tests,
                )
                self.assertSetEqual(
                    {f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}MaxMacro"},
                    excluded_tests,
                )
                self.assertDictEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax": [
                            f"src{os.sep}foo.h::::Foo::Maximum(int,int)"
                        ],
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max": [
                            f"src{os.sep}foo.h::::::Max(int,int)"
                        ],
                    },
                    selection_causes,
                )

    def test_selection_delete_file(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                (
                    function_lookup_table,
                    test_function_traces,
                ) = setup_repo_init_lookup_traces(git_client=git_client)

                # set up RTS algo
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=function_lookup_table,
                    test_function_traces=test_function_traces,
                    output_dir=git_client.root,
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                file = Path("src") / "foo.h"
                file.unlink()

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Remove foo.h")

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max",
                    },
                    included_tests,
                )
                self.assertSetEqual(
                    {f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}MaxMacro"},
                    excluded_tests,
                )
                self.assertDictEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax": [
                            f"src{os.sep}foo.h::::Foo::Maximum(int,int)"
                        ],
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max": [
                            f"src{os.sep}foo.h::::::Max(int,int)"
                        ],
                    },
                    selection_causes,
                )

    def test_selection_new_virtual_override(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                (
                    function_lookup_table,
                    test_function_traces,
                ) = setup_repo_init_lookup_traces(git_client=git_client)

                # set up RTS algo
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=function_lookup_table,
                    test_function_traces=test_function_traces,
                    output_dir=git_client.root,
                    virtual_analysis=True,
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                file = Path("src") / "foo.h"
                file.write_text(
                    file.read_text()
                    + """
class Bar: Foo {
public:
	virtual int Maximum(int a, int b) override {
		return a > b ? a : b;
	}
};"""
                )

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Override Foo with Bar")

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(
                    {f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax"},
                    included_tests,
                )
                self.assertSetEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}MaxMacro",
                    },
                    excluded_tests,
                )
                self.assertDictEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax": [
                            f"src{os.sep}foo.h::::Foo::Maximum(int,int)"
                        ]
                    },
                    selection_causes,
                )

    def test_selection_new_overload(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                (
                    function_lookup_table,
                    test_function_traces,
                ) = setup_repo_init_lookup_traces(git_client=git_client)

                # set up RTS algo
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=function_lookup_table,
                    test_function_traces=test_function_traces,
                    overload_analysis=True,
                    output_dir=git_client.root,
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                file = Path("src") / "foo.h"
                file.write_text(
                    file.read_text()
                    + """
short Max(short c, short d) {
	return c > d ? c : d;
}
"""
                )
                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(
                    message="Add 2nd Max function with other signature"
                )

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max",
                    },
                    included_tests,
                )
                self.assertSetEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}MaxMacro",
                    },
                    excluded_tests,
                )
                self.assertDictEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax": [
                            f"src{os.sep}foo.h::::Foo::Maximum(int,int)"
                        ],
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max": [
                            f"src{os.sep}foo.h::::::Max(int,int)"
                        ],
                    },
                    selection_causes,
                )

    def test_selection_new_virtual_override_in_declaration(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                (
                    function_lookup_table,
                    test_function_traces,
                ) = setup_repo_init_lookup_traces(git_client=git_client)

                # set up RTS algo
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=function_lookup_table,
                    test_function_traces=test_function_traces,
                    output_dir=git_client.root,
                    virtual_analysis=True,
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                file = Path("src") / "foo.h"
                file.write_text(
                    file.read_text()
                    + """
class Bar: Foo {
public:
    virtual int Maximum(int a, int b) override;
};

int Bar::Maximum(int a, int b) {
    return a > b ? a : b;
}
"""
                )

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(
                    message="Override Foo with Bar Prototype"
                )

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(
                    {f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax"},
                    included_tests,
                )
                self.assertSetEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}MaxMacro",
                    },
                    excluded_tests,
                )
                self.assertDictEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax": [
                            f"src{os.sep}foo.h::::Foo::Maximum(int,int)"
                        ]
                    },
                    selection_causes,
                )

    def test_selection_suite_setup_change(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                (
                    function_lookup_table,
                    test_function_traces,
                ) = setup_repo_init_lookup_traces(git_client=git_client)

                # set up RTS algo
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=function_lookup_table,
                    test_function_traces=test_function_traces,
                    output_dir=git_client.root,
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                file = Path("src") / "test.h"
                file.write_text(
                    file.read_text().replace("std::cout", "int c = 0;\nstd::cout")
                )

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Change setup of test suite")

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}MaxMacro",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax",
                    },
                    included_tests,
                )
                self.assertSetEqual(set(), excluded_tests)
                self.assertDictEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}*": [
                            f"src{os.sep}test.h::::FooSuite::SetUpTestSuite()"
                        ],
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max": [],
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}MaxMacro": [],
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax": [],
                    },
                    selection_causes,
                )

    def test_selection_macros_deactivated(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                (
                    function_lookup_table,
                    test_function_traces,
                ) = setup_repo_init_lookup_traces(git_client=git_client)

                # set up RTS algo
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=function_lookup_table,
                    test_function_traces=test_function_traces,
                    output_dir=git_client.root,
                    non_functional_analysis=False,
                    non_functional_retest_all=False,
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                file = Path("src") / "test.h"
                file.write_text(
                    file.read_text().replace("a > b ? a : b", "c > b ? c : b")
                )

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Modify macro")

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(set(), included_tests)
                self.assertSetEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}MaxMacro",
                    },
                    excluded_tests,
                )
                self.assertDictEqual(
                    {},
                    selection_causes,
                )

    def test_selection_macros_retest_all(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                (
                    function_lookup_table,
                    test_function_traces,
                ) = setup_repo_init_lookup_traces(git_client=git_client)

                # set up RTS algo
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=function_lookup_table,
                    test_function_traces=test_function_traces,
                    output_dir=git_client.root,
                    non_functional_analysis=False,
                    non_functional_retest_all=True,
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                file = Path("src") / "test.h"
                file.write_text(
                    file.read_text().replace("a > b ? a : b", "c > b ? c : b")
                )

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Modify macro")

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual({"*"}, included_tests)
                self.assertSetEqual(set(), excluded_tests)
                self.assertDictEqual(
                    {"*": [f"Modify non-functional src{os.sep}test.h"]},
                    selection_causes,
                )

    def test_selection_macros(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                (
                    function_lookup_table,
                    test_function_traces,
                ) = setup_repo_init_lookup_traces(git_client=git_client)

                # set up RTS algo
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=function_lookup_table,
                    test_function_traces=test_function_traces,
                    output_dir=git_client.root,
                    non_functional_analysis=True,
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                file = Path("src") / "test.h"
                file.write_text(
                    file.read_text().replace("a > b ? a : b", "c > b ? c : b")
                )

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Modify macro")

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(
                    {f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}MaxMacro"},
                    included_tests,
                )
                self.assertSetEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax",
                    },
                    excluded_tests,
                )
                self.assertDictEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}MaxMacro": [
                            f"src{os.sep}test.cpp::::::TEST_F(FooSuite,MaxMacro)"
                        ]
                    },
                    selection_causes,
                )

    def test_selection_macro_override(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                (
                    function_lookup_table,
                    test_function_traces,
                ) = setup_repo_init_lookup_traces(git_client=git_client)

                # set up RTS algo
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=function_lookup_table,
                    test_function_traces=test_function_traces,
                    output_dir=git_client.root,
                    non_functional_analysis=True,
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                file = Path("src") / "test.cpp"
                file.write_text(
                    file.read_text().replace(
                        '#include "foo.h"',
                        '#include "foo.h"\n#define Max(a, b) a > b ? a : b',
                    )
                )

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Override function with macro")

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max",
                    },
                    included_tests,
                )
                self.assertSetEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}MaxMacro",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax",
                    },
                    excluded_tests,
                )
                self.assertDictEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max": [
                            f"src{os.sep}foo.h::::::Max(int,int)",
                            f"src{os.sep}test.cpp::::::TEST_F(FooSuite,Max)",
                        ],
                    },
                    selection_causes,
                )

    def test_selection_scope_override_local_namespace(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                # create initial commit on main branch
                file: Path = git_client.root / "test.cpp"
                file.write_text(
                    """
#include <gtest/gtest.h>

int max(int a, int b) {
    return a;
}

namespace {
    int maximum(int a, int b) {
        return max(a, b);
    }
}

TEST_F(Foo, Max) {
    ASSERT_EQ(maximum(1,2), 1);
}
"""
                )
                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Initial Commit")
                git_client.git_repo.git.push()

                # create lookup and traces
                function_lookup_table: Dict[str, List[CoveredFunction]] = {
                    f"test.cpp": [
                        CoveredFunction(
                            0, f"test.cpp", "max(int,int)", 3, 5, None, None, None
                        ),
                        CoveredFunction(
                            1,
                            f"test.cpp",
                            "maximum(int,int)",
                            8,
                            10,
                            None,
                            "anon",
                            None,
                        ),
                        CoveredFunction(
                            2,
                            f"test.cpp",
                            "TEST_F(Foo,Max)",
                            13,
                            15,
                            None,
                            None,
                            None,
                        ),
                    ],
                }
                test_function_traces: Dict[str, Set[int]] = {
                    f"sample_module{TEST_ID_SEP}Foo{TEST_ID_SEP}Max": {0, 1, 2},
                }

                # set up RTS algo
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=FunctionLookupTable(
                        table=function_lookup_table
                    ),
                    test_function_traces=TestFunctionTraces(table=test_function_traces),
                    output_dir=git_client.root,
                    non_functional_analysis=False,
                    scope_analysis=True,
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                file.write_text(
                    file.read_text().replace(
                        "namespace {",
                        """namespace {
                    int max(int a, int b) { return b; }
                    """,
                    )
                )

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(
                    message="Add namespace local function that overrides global"
                )

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(
                    {f"sample_module{TEST_ID_SEP}Foo{TEST_ID_SEP}Max"}, included_tests
                )
                self.assertSetEqual(set(), excluded_tests)

    def test_selection_with_generated_code(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                # create initial commit on main branch
                test_file: Path = git_client.root / "test.cpp"
                test_file.write_text(
                    """
#include <gtest/gtest.h>
#include "generated.h"

TEST_F(Foo, Max) {
    ASSERT_EQ(max_gen(1,2), 2);
}
"""
                )
                gen_file: Path = git_client.root / "foo.ui"
                gen_file.touch()
                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Initial Commit")
                git_client.git_repo.git.push()

                # create lookup and traces
                function_lookup_table: Dict[str, List[CoveredFunction]] = {
                    "test.cpp": [
                        CoveredFunction(
                            0,
                            "test.cpp",
                            "TEST_F(Foo,Max)",
                            4,
                            6,
                            None,
                            None,
                            None,
                        ),
                    ],
                    f"gen{os.sep}generated.cpp": [
                        CoveredFunction(
                            1,
                            f"gen{os.sep}generated.cpp",
                            "max_gen(int,int)",
                            1,
                            3,
                            None,
                            None,
                            None,
                        ),
                    ],
                }
                test_function_traces: Dict[str, Set[int]] = {
                    f"sample_module{TEST_ID_SEP}Foo{TEST_ID_SEP}Max": {0, 1},
                }

                # set up RTS algo
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=FunctionLookupTable(
                        table=function_lookup_table
                    ),
                    test_function_traces=TestFunctionTraces(table=test_function_traces),
                    output_dir=git_client.root,
                    non_functional_analysis=False,
                    scope_analysis=False,
                    generated_code_regex=".*gen.*",
                    generated_code_exts=[".ui"],
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                gen_file.write_text("""foo""")

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(
                    message="Change source for generated code (.ui file)"
                )

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(
                    {f"sample_module{TEST_ID_SEP}Foo{TEST_ID_SEP}Max"}, included_tests
                )
                self.assertSetEqual(set(), excluded_tests)

    def test_selection_with_retest_all(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                # create initial commit on main branch
                test_file: Path = git_client.root / "test.cpp"
                test_file.write_text(
                    """
#include <gtest/gtest.h>

TEST_F(Foo, Max) {
    ASSERT_EQ(true, true);
}
"""
                )
                config_file: Path = git_client.root / "config" / "foo.h"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.touch()
                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Initial Commit")
                git_client.git_repo.git.push()

                # create lookup and traces
                function_lookup_table: Dict[str, List[CoveredFunction]] = {
                    "test.cpp": [
                        CoveredFunction(
                            0,
                            "test.cpp",
                            "TEST_F(Foo,Max)",
                            4,
                            6,
                            None,
                            None,
                            None,
                        ),
                    ],
                }
                test_function_traces: Dict[str, Set[int]] = {
                    f"sample_module{TEST_ID_SEP}Foo{TEST_ID_SEP}Max": {0},
                }

                # set up RTS algo
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=FunctionLookupTable(
                        table=function_lookup_table
                    ),
                    test_function_traces=TestFunctionTraces(table=test_function_traces),
                    output_dir=git_client.root,
                    retest_all_regex=".*config.*",
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                config_file.write_text("""foo""")

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(
                    message="Change source for config file with retest-all"
                )

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual({"*"}, included_tests)
                self.assertSetEqual(set(), excluded_tests)
                self.assertDictEqual(
                    {
                        f"*": [
                            f"{SelectionCause.RETEST_ALL_REGEX.value} {config_file.relative_to(git_client.root).__str__()}"
                        ]
                    },
                    selection_causes,
                )

    def test_selection_with_file_level_regex(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)

                # create initial commit on main branch
                test_file: Path = git_client.root / "foo" / "test.cpp"
                test_file.parent.mkdir(parents=True, exist_ok=True)
                test_file.touch()
                test_file.write_text(
                    """
#include <gtest/gtest.h>

TEST_F(Foo, Max) {
    ASSERT_EQ(true, true);
}
"""
                )
                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Initial Commit")
                git_client.git_repo.git.push()

                # create lookup and traces
                function_lookup_table: Dict[str, List[CoveredFunction]] = {
                    f"foo{os.sep}test.cpp": [
                        CoveredFunction(
                            0,
                            f"foo{os.sep}test.cpp",
                            "TEST_F(Foo,Max)",
                            4,
                            6,
                            None,
                            None,
                            None,
                        ),
                    ],
                }
                test_function_traces: Dict[str, Set[int]] = {
                    f"sample_module{TEST_ID_SEP}Foo{TEST_ID_SEP}Max": {0},
                }

                # set up RTS algo
                algo: CppFunctionLevelRTS = CppFunctionLevelRTS(
                    git_client=git_client,
                    function_lookup_table=FunctionLookupTable(
                        table=function_lookup_table
                    ),
                    test_function_traces=TestFunctionTraces(table=test_function_traces),
                    output_dir=git_client.root,
                    file_level_regex=".*foo.*",
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                test_file.write_text(test_file.read_text() + """\nint i = 1;\n""")

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(
                    message="Change source file with file-level regex"
                )

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(
                    {f"sample_module{TEST_ID_SEP}Foo{TEST_ID_SEP}Max"}, included_tests
                )
                self.assertSetEqual(set(), excluded_tests)
                self.assertDictEqual(
                    {
                        f"sample_module{TEST_ID_SEP}Foo{TEST_ID_SEP}Max": [
                            f"foo{os.sep}test.cpp::::::TEST_F(Foo,Max)"
                        ]
                    },
                    selection_causes,
                )


if __name__ == "__main__":
    unittest.main()
