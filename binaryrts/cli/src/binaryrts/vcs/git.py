import logging
import os
import re
import subprocess as sb
from contextlib import contextmanager
from pathlib import Path
from typing import List, Dict, Optional, Generator, Tuple, Pattern, Set

from git import Repo

from binaryrts.util.fs import temp_path
from binaryrts.util.process import check_executable_exists
from binaryrts.vcs.base import ChangelistItem, ChangelistItemAction, Changelist


class GitClient:
    # mappings from log/show
    # https://mirrors.edge.kernel.org/pub/software/scm/git/docs/git-diff-tree.html#_raw_output_format
    action_mapping: Dict[str, ChangelistItemAction] = {
        "A": ChangelistItemAction.ADDED,
        "?": ChangelistItemAction.ADDED,
        "C": ChangelistItemAction.ADDED,  # copy of a file into a new one, followed by score
        "D": ChangelistItemAction.DELETED,
        "!": ChangelistItemAction.DELETED,
        "M": ChangelistItemAction.MODIFIED,
        "R": ChangelistItemAction.MODIFIED,  # renaming, followed by score, e.g. R095 for 95%
        "T": ChangelistItemAction.MODIFIED,  # change in the type of the file
    }

    diff_pattern: Pattern = re.compile(r"^diff --git a/(?P<filepath>.*) b/.*$")

    def __init__(
        self,
        root: Path,
        use_cache: bool = True,
    ) -> None:
        if not check_executable_exists("git"):
            raise Exception("Cannot find git executable.")
        self.root = root
        self.git_repo: Repo = Repo(path=root)
        # to reduce latency in slow (big) git repos, we cache results from git commands
        self.use_cache = use_cache
        self.diff_cache: Dict[str, Changelist] = {}
        self.show_cache: Dict[str, str] = {}

    @classmethod
    def from_repo(cls, git_repo: Repo) -> "GitClient":
        return cls(root=Path(git_repo.git_dir).resolve(strict=True).parent)

    def get_file_content_at_revision(self, revision: str, filepath: Path) -> str:
        valid_filepath: str = str(
            filepath.relative_to(Path(self.root).absolute())
            if filepath.is_absolute()
            else filepath
        ).replace(os.sep, "/")
        git_obj: str = f"{revision}:{valid_filepath}"
        if self.use_cache and git_obj in self.show_cache:
            return self.show_cache[git_obj]
        logging.debug(f"Calling git show {git_obj}")
        raw_output: str = (
            sb.check_output(
                ["git", "-C", self.root.__str__(), "show", git_obj], text=True, encoding="utf-8"
            )
            .encode("utf-8")
            .decode("utf-8-sig")
        )  # fixes unicode encoding issues on Windows with BOM
        if self.use_cache and git_obj not in self.show_cache:
            self.show_cache[git_obj] = raw_output
        return raw_output

    def parse_diff(self, diff: str) -> Changelist:
        items: Set[ChangelistItem] = set()
        output_lines = diff.splitlines()
        for idx, line in enumerate(output_lines):
            # fast-path without regex
            if "diff --git" not in line:
                continue

            match = re.search(self.diff_pattern, line)
            if match is None:
                continue
            filepath: str = match.group("filepath")
            action: ChangelistItemAction = ChangelistItemAction.MODIFIED
            if len(output_lines) > idx + 1:
                if "new file mode" in output_lines[idx + 1]:
                    action = ChangelistItemAction.ADDED
                elif "deleted file mode" in output_lines[idx + 1]:
                    action = ChangelistItemAction.DELETED
            items.add(ChangelistItem(filepath=Path(filepath), action=action))

        changelist: Changelist = Changelist(items=list(items))
        logging.debug(
            "git diff has changelist with %d items:\n%s"
            % (
                len(changelist.items),
                "\n".join(
                    map(lambda i: f"{i.action.value} {i.filepath}", changelist.items)
                ),
            )
        )
        return changelist

    def get_diff(
        self,
        from_revision: str,
        to_revision: str,
    ) -> Changelist:
        # We use the three-dot diff here to figure out the diff between the latest common ancestor and the pull request.
        # This will make sure to only consider changes made inside a pull request and no changes from the target branch.
        git_obj: str = f"{from_revision}...{to_revision}"
        if self.use_cache and git_obj in self.diff_cache:
            return self.diff_cache[git_obj]
        command: List[str] = [
            "git",
            "-C",
            self.root.__str__(),
            "diff",
            "--no-renames",
            "--unified=0",
            "--no-color",
            "--ignore-cr-at-eol",
            "--ignore-space-at-eol",
            "--ignore-space-change",
            "--ignore-all-space",
            git_obj,
        ]
        raw_output: str = sb.check_output(command, text=True, encoding="utf-8")
        cl: Changelist = self.parse_diff(diff=raw_output)
        if self.use_cache and git_obj not in self.diff_cache:
            self.diff_cache[git_obj] = cl
        return cl

    def get_status(self) -> Changelist:
        raw_output: str = sb.check_output(
            ["git", "-C", self.root.__str__(), "status", "--porcelain"], text=True
        )
        changes: List[List[str]] = list(
            map(
                lambda c: c.split(),
                raw_output.splitlines(),
            )
        )
        return Changelist(
            items=[
                ChangelistItem(
                    action=self._get_changelist_item_action(change[0]),
                    filepath=Path(change[1]),
                )
                for change in changes
                if len(change) > 0
            ]
        )

    @classmethod
    def _get_changelist_item_action(cls, status_chars: str) -> ChangelistItemAction:
        # set default
        action: ChangelistItemAction = ChangelistItemAction.MODIFIED
        # get status from first char
        if len(status_chars) > 0:
            action = cls.action_mapping[status_chars[0]]
        return action


def get_repo_root(path: Path) -> Path:
    root: Path = path
    if not is_git_repo(root):
        raise Exception(f"Did not provide initial valid git repository at {path}.")
    while is_git_repo(path=root.parent.absolute()):
        root = root.parent
        logging.debug(f"Found git repo at {root}, continuing to move upwards.")
    return root


def is_git_repo(path: Path) -> bool:
    result: bool = False

    if not check_executable_exists("git"):
        logging.debug("Could not find git executable.")
        return result

    return (
        sb.call(
            ["git", "-C", path.__str__(), "status"],
            stderr=sb.STDOUT,
            stdout=open(os.devnull, "w"),
        )
        == 0
    )


@contextmanager
def clone_repo_if_not_exists(path: str) -> Generator[Repo, None, None]:
    """
    Will create a temporary clone of a git repository if the provided path is not local.
    Caller will need to take care of removing the directory again.

    Example:

    ```
    repo = clone_repo_if_not_exists(path)
    shutil.rmtree(repo.working_dir)
    ```

    :param path: URL or FS path
    :return:
    """
    git_repo = Repo(path)
    if not git_repo.bare:
        yield git_repo

    with temp_clone(repo_path=path) as (repo_path, _):
        yield Repo(repo_path)


@contextmanager
def temp_repo(
    mkdir: bool = False,
) -> Generator[Tuple[str, Repo], None, None]:
    """
    Initialize a repository in the current path (i.e., the git remote).
    """
    with temp_path() as repo_path:
        repo: Repo = Repo.init(path=repo_path, mkdir=mkdir, bare=True)
        yield repo_path, repo


@contextmanager
def temp_clone(
    repo_path: Optional[str] = None,
) -> Generator[Tuple[str, Repo], None, None]:
    """
    Clones a repository in the current path to a temporary location.

    :param repo_path:
    """
    path: str = repo_path if repo_path else os.getcwd()

    with temp_path() as working_path:
        repo: Repo = Repo.clone_from(url=path, to_path=working_path)
        yield working_path, repo
