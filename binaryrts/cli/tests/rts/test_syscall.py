import os
import unittest
from pathlib import Path

from binaryrts.parser.coverage import TestFileTraces, TEST_ID_SEP
from binaryrts.rts.syscall import SyscallFileLevelRTS
from binaryrts.vcs.git import GitClient, temp_repo, temp_clone

RESOURCES_DIR: Path = Path(os.path.dirname(__file__)) / "resources"
SAMPLE_MODULE_DIR: Path = RESOURCES_DIR / "sample_module"


class SyscallFileLevelRTSTestCase(unittest.TestCase):
    def test_selection_file_modification(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)
                file: Path = Path("test.txt")
                file.touch()
                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Create empty file")
                git_client.git_repo.git.push()

                test_file_traces: TestFileTraces = TestFileTraces(
                    table={
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}*": {
                            Path("foo.txt").__str__()
                        },
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax": {
                            file.__str__()
                        },
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max": {
                            Path("bar.txt").__str__()
                        },
                    }
                )

                # set up RTS algo
                algo: SyscallFileLevelRTS = SyscallFileLevelRTS(
                    git_client=git_client,
                    test_file_traces=test_file_traces,
                    output_dir=git_client.root,
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                file.write_text("test")

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Modify file")

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(
                    {f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax"},
                    included_tests,
                )
                self.assertSetEqual(
                    {f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max"},
                    excluded_tests,
                )
                self.assertDictEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax": [
                            file.__str__()
                        ]
                    },
                    selection_causes,
                )

    def test_excludes(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)
                file: Path = Path("test.txt")
                file.touch()
                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Create empty file")
                git_client.git_repo.git.push()

                test_file_traces: TestFileTraces = TestFileTraces(
                    table={
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}*": {
                            Path("foo.txt").__str__()
                        },
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax": {
                            file.__str__()
                        },
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max": {
                            Path("bar.txt").__str__()
                        },
                    }
                )

                # set up RTS algo
                algo: SyscallFileLevelRTS = SyscallFileLevelRTS(
                    git_client=git_client,
                    test_file_traces=test_file_traces,
                    output_dir=git_client.root,
                    excludes_regex=".*",
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                file.write_text("test")

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Modify file")

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(set(), included_tests)
                self.assertSetEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax",
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max",
                    },
                    excluded_tests,
                )
                self.assertDictEqual(
                    dict(),
                    selection_causes,
                )

    def test_selection_file_removal(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                git_client: GitClient = GitClient.from_repo(git_repo=local_repo)
                file: Path = Path("test.txt")
                file.touch()
                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Create empty file")
                git_client.git_repo.git.push()

                test_file_traces: TestFileTraces = TestFileTraces(
                    table={
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}*": {
                            Path("foo.txt").__str__()
                        },
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax": {
                            file.__str__()
                        },
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max": {
                            Path("bar.txt").__str__()
                        },
                    }
                )

                # set up RTS algo
                algo: SyscallFileLevelRTS = SyscallFileLevelRTS(
                    git_client=git_client,
                    test_file_traces=test_file_traces,
                    output_dir=git_client.root,
                )

                # checkout feature branch
                target_branch: str = git_client.git_repo.active_branch.name
                git_client.git_repo.git.checkout(b="feature/xxx")

                file.unlink()

                git_client.git_repo.git.add(".")
                git_client.git_repo.git.commit(message="Delete file")

                included_tests, excluded_tests, selection_causes = algo.select_tests(
                    from_revision=target_branch, to_revision="HEAD"
                )
                self.assertSetEqual(
                    {f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax"},
                    included_tests,
                )
                self.assertSetEqual(
                    {f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Max"},
                    excluded_tests,
                )
                self.assertDictEqual(
                    {
                        f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}FooMax": [
                            file.__str__()
                        ]
                    },
                    selection_causes,
                )


if __name__ == "__main__":
    unittest.main()
