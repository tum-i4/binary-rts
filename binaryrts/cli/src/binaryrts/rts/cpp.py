import logging
import re
from abc import ABC
from pathlib import Path
from typing import List, Optional, Tuple, Set, Dict, Any

from binaryrts.parser.coverage import (
    FunctionLookupTable,
    TestFunctionTraces,
    CoveredFunction,
)
from binaryrts.parser.sourcecode import (
    FunctionDefinition,
    CSourceCodeParser,
    NonFunctionalCallAnalyzer,
    NonFunctionalCallSite,
)
from binaryrts.rts.base import RTSAlgo, SelectionCause
from binaryrts.rts.diff import CodeDiffAnalyzer
from binaryrts.util.fs import temp_file, get_parent, has_ext
from binaryrts.vcs.base import Changelist, ChangelistItemAction, ChangelistItem
from binaryrts.vcs.git import GitClient


class CppBaseRTS(RTSAlgo, ABC):
    def __init__(
        self,
        function_lookup_table: FunctionLookupTable,
        test_function_traces: TestFunctionTraces,
        git_client: GitClient,
        output_dir: Path,
        includes_regex: str = ".*",
        excludes_regex: str = "",
        generated_code_regex: Optional[str] = None,
        generated_code_exts: Optional[List[str]] = None,
        retest_all_regex: Optional[str] = None,
    ) -> None:
        super().__init__(
            git_client=git_client,
            output_dir=output_dir,
            includes_regex=includes_regex,
            excludes_regex=excludes_regex,
            generated_code_regex=generated_code_regex,
            generated_code_exts=generated_code_exts,
            retest_all_regex=retest_all_regex,
        )
        self.function_lookup_table = function_lookup_table
        self.test_function_traces = test_function_traces

    def check_retest_all(self, item: ChangelistItem) -> bool:
        return (
            self.retest_all_regex
            and re.match(self.retest_all_regex, item.filepath.__str__(), re.IGNORECASE)
            is not None
        )

    def check_generated_code(self, item: ChangelistItem) -> bool:
        return (
            self.generated_code_exts is not None
            and self.generated_code_regex is not None
            and has_ext(item.filepath, self.generated_code_exts)
        )

    def check_file_excluded(self, item: ChangelistItem) -> bool:
        return (
            not CSourceCodeParser.is_c_file(item.filepath)
            or not re.match(self.includes_regex, item.filepath.__str__(), re.IGNORECASE)
            or (
                self.excludes_regex != ""
                and re.match(
                    self.excludes_regex, item.filepath.__str__(), re.IGNORECASE
                )
            )
        )


class CppFileLevelRTS(CppBaseRTS):
    def __init__(
        self,
        function_lookup_table: FunctionLookupTable,
        test_function_traces: TestFunctionTraces,
        git_client: GitClient,
        output_dir: Path,
        includes_regex: str = ".*",
        excludes_regex: str = "",
        generated_code_regex: Optional[str] = None,
        generated_code_exts: Optional[List[str]] = None,
        retest_all_regex: Optional[str] = None,
    ) -> None:
        super().__init__(
            function_lookup_table=function_lookup_table,
            test_function_traces=test_function_traces,
            git_client=git_client,
            output_dir=output_dir,
            includes_regex=includes_regex,
            excludes_regex=excludes_regex,
            generated_code_regex=generated_code_regex,
            generated_code_exts=generated_code_exts,
            retest_all_regex=retest_all_regex,
        )

    def select_tests(
        self, from_revision: str, to_revision: str
    ) -> Tuple[Set[str], Set[str], Dict[str, List[Any]]]:
        affected_function_ids: Set[int] = set()
        changelist: Changelist = self.git_client.get_diff(
            from_revision=from_revision, to_revision=to_revision
        )

        for change_item in changelist.items:
            if self.check_retest_all(item=change_item):
                return self._retest_all(
                    causes=[
                        SelectionCause.RETEST_ALL_REGEX.value
                        + f" {change_item.filepath}"
                    ]
                )
            if self.check_generated_code(item=change_item):
                functions: List[
                    CoveredFunction
                ] = self.function_lookup_table.find_functions_by_file_regex(
                    file_regex=self.generated_code_regex
                )
                affected_function_ids |= {func.identifier for func in functions}
                continue

            if self.check_file_excluded(item=change_item):
                continue

            if (
                change_item.action == ChangelistItemAction.DELETED
                or change_item.action == ChangelistItemAction.MODIFIED
            ):
                functions: List[
                    CoveredFunction
                ] = self.function_lookup_table.find_functions(file=change_item.filepath)
                affected_function_ids |= {func.identifier for func in functions}
        (
            included_tests,
            excluded_tests,
            selection_causes,
        ) = self.test_function_traces.select_tests(
            affected_entity_ids=affected_function_ids
        )
        selection_causes = {
            test_id: list(
                set(
                    [
                        self.function_lookup_table.get_function_by_identifier(
                            func_id
                        ).file
                        for func_id in affected_ids
                    ]
                )
            )
            for test_id, affected_ids in selection_causes.items()
        }
        return included_tests, excluded_tests, selection_causes


class CppFunctionLevelRTS(CppBaseRTS):
    def __init__(
        self,
        git_client: GitClient,
        function_lookup_table: FunctionLookupTable,
        test_function_traces: TestFunctionTraces,
        output_dir: Path,
        non_functional_analysis: bool = False,
        non_functional_analysis_depth: int = 2,
        non_functional_retest_all: bool = False,
        virtual_analysis: bool = False,
        scope_analysis: bool = False,
        overload_analysis: bool = False,
        use_cscope: bool = False,
        includes_regex: str = ".*",
        excludes_regex: str = "",
        generated_code_regex: Optional[str] = None,
        generated_code_exts: Optional[List[str]] = None,
        retest_all_regex: Optional[str] = None,
        file_level_regex: Optional[str] = None,
    ) -> None:
        super().__init__(
            function_lookup_table=function_lookup_table,
            test_function_traces=test_function_traces,
            git_client=git_client,
            output_dir=output_dir,
            includes_regex=includes_regex,
            excludes_regex=excludes_regex,
            generated_code_regex=generated_code_regex,
            generated_code_exts=generated_code_exts,
            retest_all_regex=retest_all_regex,
        )
        self.non_functional_analysis = non_functional_analysis
        self.non_functional_analysis_depth = non_functional_analysis_depth
        self.non_functional_retest_all = non_functional_retest_all
        self.scope_analysis = scope_analysis
        self.overload_analysis = overload_analysis
        self.virtual_analysis = virtual_analysis
        self.file_level_regex = file_level_regex
        self.use_cscope = use_cscope

    def _get_ids_of_affected_functions_for_file(
        self, affected_functions: List[FunctionDefinition], file: Optional[Path] = None
    ) -> Set[int]:
        logging.debug(f"Looking up affected functions: {affected_functions}")
        function_ids = set(
            sum(
                [
                    list(
                        map(
                            lambda f: f.identifier,
                            self.function_lookup_table.find_functions(
                                file=file,
                                signature=func.signature,
                                namespace=func.namespace,
                                class_name=func.class_name,
                            ),
                        )
                    )
                    for func in affected_functions
                ],
                [],
            )
        )
        return function_ids

    def _get_ids_of_affected_function_for_non_functional(
        self, symbol_name: str, root_dir: Path, file_relative_to: Optional[Path] = None
    ) -> Set[int]:
        call_analyzer: NonFunctionalCallAnalyzer = NonFunctionalCallAnalyzer(
            root_dir=root_dir, use_cscope=self.use_cscope
        )
        call_sites: List[NonFunctionalCallSite] = call_analyzer.get_call_sites(
            symbol_name=symbol_name, file_relative_to=file_relative_to
        )
        affected_function_ids: Set[int] = set()
        for site in call_sites:
            funcs: Optional[
                List[CoveredFunction]
            ] = self.function_lookup_table.find_functions_by_line(
                file=site.path, line=site.line_no
            )
            if funcs is not None and len(funcs) > 0:
                affected_function_ids |= {func.identifier for func in funcs}
        return affected_function_ids

    def _mark_all_functions_as_affected(self, change_item: ChangelistItem) -> Set[str]:
        affected_function_ids: Set[str] = set()
        if (
            self.file_level_regex
            and CSourceCodeParser.is_c_file(change_item.filepath)
            and re.match(
                self.file_level_regex, change_item.filepath.__str__(), re.IGNORECASE
            )
            is not None
        ):
            functions: List[
                CoveredFunction
            ] = self.function_lookup_table.find_functions(file=change_item.filepath)
            affected_function_ids |= {func.identifier for func in functions}
        return affected_function_ids

    def select_tests(
        self,
        from_revision: str,
        to_revision: str,
    ) -> Tuple[Set[str], Set[str], Dict[str, List[Any]]]:
        affected_function_ids: Set[int] = set()
        changelist: Changelist = self.git_client.get_diff(
            from_revision=from_revision, to_revision=to_revision
        )
        # Note: We include function prototypes here, as when parsing for changed functions,
        # we must also consider changed function declarations, which will have keywords
        # such as `override` or `virtual` in their signature, as opposed to definitions.
        parser: CSourceCodeParser = CSourceCodeParser(include_prototypes=True)
        diff_analyzer: CodeDiffAnalyzer = CodeDiffAnalyzer(
            parser=parser,
            scope_analysis=self.scope_analysis,
            overload_analysis=self.overload_analysis,
            virtual_analysis=self.virtual_analysis,
        )

        for change_item in changelist.items:
            logging.debug(
                f"Analyzing change item: {change_item.filepath} ({change_item.action})"
            )

            if self.check_retest_all(item=change_item):
                logging.debug(f"Triggering retest-all")
                return self._retest_all(
                    causes=[
                        SelectionCause.RETEST_ALL_REGEX.value
                        + f" {change_item.filepath}"
                    ]
                )

            if self.check_generated_code(item=change_item):
                logging.debug(f"Triggering generated-code handling")
                functions: List[
                    CoveredFunction
                ] = self.function_lookup_table.find_functions_by_file_regex(
                    file_regex=self.generated_code_regex
                )
                affected_function_ids |= {func.identifier for func in functions}
                continue

            if self.check_file_excluded(item=change_item):
                logging.debug(f"Triggering file excluded")
                continue

            changed_functions: List[FunctionDefinition]
            if change_item.action == ChangelistItemAction.ADDED:
                with temp_file(suffix=".cxx") as new_file:
                    with new_file.open("w+", newline="\n", encoding="utf-8") as n_fp:
                        n_fp.write(
                            self.git_client.get_file_content_at_revision(
                                revision=to_revision, filepath=change_item.filepath
                            )
                        )
                    changed_functions: List[FunctionDefinition] = parser.get_functions(
                        new_file
                    )
                    affected_function_ids |= (
                        self._get_ids_of_affected_functions_for_file(
                            affected_functions=changed_functions, file=None
                        )
                    )
                    if self.non_functional_analysis or self.non_functional_retest_all:
                        for non_func_entity in parser.get_non_functional_entities(
                            new_file
                        ):
                            if self.non_functional_retest_all:
                                return self._retest_all(
                                    causes=[
                                        SelectionCause.ADD_NON_FUNCTIONAL_FILE.value
                                        + f" {change_item.filepath}"
                                    ]
                                )
                            affected_function_ids |= (
                                self._get_ids_of_affected_function_for_non_functional(
                                    symbol_name=non_func_entity.name,
                                    root_dir=get_parent(
                                        change_item.filepath,
                                        depth=self.non_functional_analysis_depth,
                                    ),
                                    file_relative_to=self.git_client.root,
                                )
                            )

            elif change_item.action == ChangelistItemAction.DELETED:
                with temp_file(suffix=".cxx") as old_file:
                    with old_file.open("w+", newline="\n", encoding="utf-8") as o_fp:
                        o_fp.write(
                            self.git_client.get_file_content_at_revision(
                                revision=from_revision, filepath=change_item.filepath
                            )
                        )
                    changed_functions: List[FunctionDefinition] = parser.get_functions(
                        file=old_file
                    )
                    affected_function_ids |= (
                        self._get_ids_of_affected_functions_for_file(
                            affected_functions=changed_functions,
                            file=change_item.filepath,
                        )
                    )
                    if self.non_functional_analysis or self.non_functional_retest_all:
                        for non_func_entity in parser.get_non_functional_entities(
                            old_file
                        ):
                            if self.non_functional_retest_all:
                                return self._retest_all(
                                    causes=[
                                        SelectionCause.DELETE_NON_FUNCTIONAL_FILE.value
                                        + f" {change_item.filepath}"
                                    ]
                                )
                            affected_function_ids |= (
                                self._get_ids_of_affected_function_for_non_functional(
                                    symbol_name=non_func_entity.name,
                                    root_dir=get_parent(
                                        change_item.filepath,
                                        depth=self.non_functional_analysis_depth,
                                    ),
                                    file_relative_to=self.git_client.root,
                                )
                            )

            elif change_item.action == ChangelistItemAction.MODIFIED:
                with temp_file(suffix=".cxx") as new_file:
                    with temp_file(suffix=".cxx") as old_file:
                        with new_file.open(
                            "w+", newline="\n", encoding="utf-8"
                        ) as n_fp:
                            n_fp.write(
                                self.git_client.get_file_content_at_revision(
                                    revision=to_revision, filepath=change_item.filepath
                                )
                            )
                        with old_file.open(
                            "w+", newline="\n", encoding="utf-8"
                        ) as o_fp:
                            o_fp.write(
                                self.git_client.get_file_content_at_revision(
                                    revision=from_revision,
                                    filepath=change_item.filepath,
                                )
                            )
                        for func, file in [
                            *diff_analyzer.get_changed_or_newly_overridden_functions(
                                old_revision=old_file, new_revision=new_file
                            ),
                            *diff_analyzer.get_deleted_functions(
                                old_revision=old_file, new_revision=new_file
                            ),
                        ]:
                            affected_function_ids |= (
                                self._get_ids_of_affected_functions_for_file(
                                    affected_functions=[func],
                                    file=None if file is None else change_item.filepath,
                                )
                            )

                        if (
                            self.non_functional_analysis
                            or self.non_functional_retest_all
                            or self.file_level_regex
                        ):
                            is_first_entity: bool = True
                            for (
                                non_func,
                                file,
                            ) in diff_analyzer.get_changed_non_functional_entities(
                                old_revision=old_file, new_revision=new_file
                            ):
                                if self.non_functional_retest_all:
                                    return self._retest_all(
                                        causes=[
                                            SelectionCause.MODIFY_NON_FUNCTIONAL_FILE.value
                                            + f" {change_item.filepath}"
                                        ]
                                    )

                                # we only want to mark functions as affected once
                                if is_first_entity and self.file_level_regex:
                                    affected_function_ids |= (
                                        self._mark_all_functions_as_affected(
                                            change_item=change_item
                                        )
                                    )
                                is_first_entity = False

                                if self.non_functional_analysis:
                                    analysis_root_dir: Path = get_parent(
                                        change_item.filepath,
                                        depth=self.non_functional_analysis_depth,
                                    )
                                    logging.info(
                                        f"Macro analysis in {analysis_root_dir} with git repo {self.git_client.root}"
                                    )
                                    affected_function_ids |= self._get_ids_of_affected_function_for_non_functional(
                                        symbol_name=non_func.name,
                                        root_dir=analysis_root_dir,
                                        file_relative_to=self.git_client.root,
                                    )

        logging.debug(
            f"Selecting tests with {len(affected_function_ids)} affected function IDs"
        )
        (
            included_tests,
            excluded_tests,
            selection_causes,
        ) = self.test_function_traces.select_tests(
            affected_entity_ids=affected_function_ids
        )
        selection_causes = {
            test_id: [
                self.function_lookup_table.get_function_by_identifier(func_id).full_name
                for func_id in affected_ids
            ]
            for test_id, affected_ids in selection_causes.items()
        }
        return included_tests, excluded_tests, selection_causes
