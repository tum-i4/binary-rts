from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Tuple, Set, Dict, List, Any, Optional

from binaryrts.vcs.git import GitClient


class RTSAlgo(ABC):
    def __init__(
        self,
        git_client: GitClient,
        output_dir: Path,
        includes_regex: str = ".*",
        excludes_regex: str = "",
        generated_code_regex: Optional[str] = None,
        generated_code_exts: Optional[List[str]] = None,
        retest_all_regex: Optional[str] = None,
    ) -> None:
        self.git_client = git_client
        self.output_dir = output_dir
        self.includes_regex = includes_regex
        self.excludes_regex = excludes_regex
        self.generated_code_regex = generated_code_regex
        self.generated_code_exts = generated_code_exts
        self.retest_all_regex = retest_all_regex

    @classmethod
    def _retest_all(
        cls, causes: Optional[List[Any]] = None
    ) -> Tuple[Set[str], Set[str], Dict[str, List[Any]]]:
        included_tests, excluded_tests, selection_causes = (
            {"*"},
            set(),
            {"*": causes if causes is not None else [SelectionCause.UNKNOWN.value]},
        )
        return included_tests, excluded_tests, selection_causes

    @abstractmethod
    def select_tests(
        self,
        from_revision: str,
        to_revision: str,
    ) -> Tuple[Set[str], Set[str], Dict[str, List[Any]]]:
        """
        Select tests between two VCS revisions.

        @param from_revision:
        @param to_revision:
        @return: (included_tests, excluded_tests, selection_causes)
        """
        pass


class SelectionCause(Enum):
    ADD_NON_FUNCTIONAL_FILE = "Add non-functional"
    DELETE_NON_FUNCTIONAL_FILE = "Delete non-functional"
    MODIFY_NON_FUNCTIONAL_FILE = "Modify non-functional"
    RETEST_ALL_REGEX = "Retest-all regex"
    SELECTION_FAILURE = "Selection failure"
    UNKNOWN = "Unknown"
