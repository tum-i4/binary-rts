import logging
import re
from pathlib import Path
from typing import Set, Tuple, Dict, List, Any

from binaryrts.parser.coverage import TestFileTraces
from binaryrts.rts.base import RTSAlgo
from binaryrts.vcs.base import ChangelistItemAction, Changelist
from binaryrts.vcs.git import GitClient


class SyscallFileLevelRTS(RTSAlgo):
    def __init__(
        self,
        git_client: GitClient,
        output_dir: Path,
        test_file_traces: TestFileTraces,
        file_regex: str = ".*",
    ) -> None:
        super().__init__(git_client, output_dir, file_regex)
        self.test_file_traces = test_file_traces

    def select_tests(
        self, from_revision: str, to_revision: str
    ) -> Tuple[Set[str], Set[str], Dict[str, List[Any]]]:
        affected_files: Set[str] = set()
        changelist: Changelist = self.git_client.get_diff(
            from_revision=from_revision, to_revision=to_revision
        )
        file_pattern = re.compile(self.file_regex, flags=re.IGNORECASE)

        for change_item in changelist.items:
            if not file_pattern.match(change_item.filepath.__str__()):
                continue
            if (
                change_item.action == ChangelistItemAction.DELETED
                or change_item.action == ChangelistItemAction.MODIFIED
            ):
                affected_files.add(change_item.filepath.name.__str__().lower())
        logging.debug(
            f"Selecting tests with affected files {affected_files}"
        )
        included_tests, excluded_tests, selection_causes = self.test_file_traces.select_tests(
            affected_entity_ids=affected_files
        )
        return included_tests, excluded_tests, selection_causes
