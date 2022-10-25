import logging
import re
import subprocess as sb
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Set, List, Pattern, Tuple, Dict, Any

from binaryrts.parser.sourcecode import (
    CSourceCodeParser,
    FunctionDefinition,
    PROTOTYPE_PREFIX,
)
from binaryrts.util import dict_equals
from binaryrts.util.fs import is_relative_to
from binaryrts.util.os import os_is_windows
from binaryrts.util.process import check_executable_exists
from binaryrts.util.serialization import SerializerMixin
from binaryrts.util.string import remove_prefix

# CSV-based output
FUNCTION_LOOKUP_FILE: str = "function-lookup.csv"
TEST_LOOKUP_FILE: str = "test-lookup.csv"
TEST_FUNCTION_TRACES_FILE: str = "test-function-traces.csv"
TEST_FILE_TRACES_FILE: str = "test-file-traces.csv"

# pickle-based output
PICKLE_TEST_FUNCTION_TRACES_FILE: str = "test-function-traces.pkl"
PICKLE_FUNCTION_LOOKUP_FILE: str = "function-lookup.pkl"
PICKLE_TEST_FILE_TRACES_FILE: str = "test-file-traces.pkl"

# constants
CSV_SEP: str = ";"
COVERAGE_SEP: str = "\t"
TEST_RESULT_SEP: str = "___"
TEST_SUITE_CASE_SEP: str = "."
TEST_ID_SEP: str = "!!!"
GLOBAL_TEST_SETUP: str = "GLOBAL_TEST_SETUP"


@dataclass()
class CoveredLine:
    file: Path
    symbol_name: str
    line: int

    def __eq__(self, o: "CoveredLine") -> bool:
        return self.file == o.file and self.line == o.line

    def __hash__(self) -> int:
        return hash(f"{self.file}{self.line}")


@dataclass(unsafe_hash=True)
class CoveredFunction:
    identifier: int
    file: str
    signature: str
    start: int
    end: int
    properties: Optional[str] = field(default=None)
    namespace: Optional[str] = field(default=None)
    class_name: Optional[str] = field(default=None)

    @property
    def full_name(self) -> str:
        return f"{self.file}::{self.namespace or ''}::{self.class_name or ''}::{self.signature}"

    @classmethod
    def from_string(cls, string: str) -> "CoveredFunction":
        (
            identifier,
            file,
            signature,
            start,
            end,
            properties,
            namespace,
            class_name,
        ) = string.split(CSV_SEP)
        if properties == "None":
            properties = None
        if namespace == "None":
            namespace = None
        if class_name == "None":
            class_name = None
        return cls(
            int(identifier),
            file,
            signature,
            int(start),
            int(end),
            properties,
            namespace,
            class_name,
        )


@dataclass()
class TestCoverage:
    test_module: str
    test_suite: str
    test_case: Optional[str] = field(default=None)
    test_result: Optional[str] = field(default=None)
    covered_lines: Set[CoveredLine] = field(default_factory=set)
    covered_files: Set[Path] = field(default_factory=set)


def get_test_id(
    test_module: str,
    test_suite: Optional[str] = None,
    test_case: Optional[str] = None,
) -> str:
    """
    Helper function to concatenate test identifier fragments into identifier.
    @param test_module:
    @param test_suite:
    @param test_case:
    @return:
    """
    test_id: str = test_module
    if test_suite is not None and test_suite != "":
        test_id += f"{TEST_ID_SEP}{test_suite}"
    if test_case is not None and test_case != "":
        test_id += f"{TEST_ID_SEP}{test_case}"
    return test_id


def from_test_id(test_id: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Helper function to extract test identifier fragments from identifier.
    @param test_id:
    @return:
    """
    test_fragments = test_id.split(TEST_ID_SEP)
    test_module: str = test_fragments[0]
    test_suite: Optional[str] = None
    test_case: Optional[str] = None
    if len(test_fragments) > 1:
        test_suite = test_fragments[1]
    if len(test_fragments) > 2:
        test_case = test_fragments[2]
    return test_module, test_suite, test_case


class FunctionLookupTable(SerializerMixin):
    """
    The function lookup table is a hashtable which uses the functions' files as keys:

    {
        "foo.cpp": [{ name: "bar()", start: 10, end: 15, ...}],
        "bar.cpp": ...
    }
    """

    def __init__(
        self,
        table: Optional[Dict[str, List[CoveredFunction]]] = None,
        root_dir: Optional[Path] = None,
        all_functions: Optional[List[CoveredFunction]] = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        if table is not None:
            self.table: Dict[str, List[CoveredFunction]] = table
        else:
            self.table: Dict[str, List[CoveredFunction]] = {}
        self.root_dir = root_dir
        self.all_functions_ordered_by_id: List[CoveredFunction]
        if all_functions is not None:
            self.all_functions_ordered_by_id = sorted(
                all_functions, key=lambda x: x.identifier
            )
        else:
            self.all_functions_ordered_by_id = sorted(
                sum(self.table.values(), []), key=lambda x: x.identifier
            )
        # cache lookup table by function name
        self.function_cache: Dict[str, List[CoveredFunction]] = {}
        self.update_function_cache()

        self.max_id: int = (
            0  # 0-indexed, so we can comfortably perform constant-time lookups by id
        )
        if len(self.all_functions_ordered_by_id) > 0:
            self.max_id = self.all_functions_ordered_by_id[-1].identifier

    def __setstate__(self, state):
        self.__dict__ = state
        # we remove the root_dir attribute when deserializing, to make read-only scenarios faster,
        # that would otherwise always have to check for relative paths
        self.root_dir = None
        self.update_function_cache()

    def _relativize_filepath_to_key(self, filepath: Path) -> str:
        file_key: str
        if self.root_dir is not None and is_relative_to(filepath, self.root_dir):
            file_key = filepath.relative_to(self.root_dir).__str__()
        else:
            file_key = filepath.__str__()
        return file_key

    def update_function_cache(self):
        for func in self.all_functions_ordered_by_id:
            if func.signature not in self.function_cache:
                self.function_cache[func.signature] = []
            self.function_cache[func.signature].append(func)

    def to_csv(self, file: Path):
        with file.open("w+") as csv_file:
            for function_file, functions in self.table.items():
                for func in functions:
                    csv_file.write(
                        f"{func.identifier}{CSV_SEP}"
                        f"{function_file}{CSV_SEP}"
                        f"{func.signature}{CSV_SEP}"
                        f"{func.start}{CSV_SEP}"
                        f"{func.end}{CSV_SEP}"
                        f"{func.properties}{CSV_SEP}"
                        f"{func.namespace}{CSV_SEP}"
                        f"{func.class_name}"
                        f"\n"
                    )

    @classmethod
    def from_csv(
        cls, file: Path, root_dir: Optional[Path] = None
    ) -> "FunctionLookupTable":
        table: Dict[str, List[CoveredFunction]] = {}
        all_functions: List[CoveredFunction] = []
        with file.open("r") as csv_file:
            for line in csv_file:
                func = CoveredFunction.from_string(line.strip())
                if (
                    Path(func.file).is_absolute()
                    and root_dir is not None
                    and is_relative_to(file, root_dir)
                ):
                    func.file = Path(func.file).relative_to(root_dir).__str__()
                if func.file not in table:
                    table[func.file] = []
                table[func.file].append(func)
                all_functions.append(func)
        return cls(table=table, root_dir=root_dir, all_functions=all_functions)

    def find_functions_by_file_regex(self, file_regex: str) -> List[CoveredFunction]:
        functions: List[CoveredFunction] = []
        regex: Pattern = re.compile(file_regex, re.IGNORECASE)
        for file_key, file_functions in self.table.items():
            if regex.match(file_key):
                functions += file_functions
        return functions

    def find_functions(
        self,
        file: Optional[Path] = None,
        signature: Optional[str] = None,
        namespace: Optional[str] = None,
        class_name: Optional[str] = None,
    ) -> List[CoveredFunction]:
        functions: List[CoveredFunction] = []

        # make sure we query by the correct function name, not an intermediate prototype name
        if signature is not None and signature.startswith(PROTOTYPE_PREFIX):
            signature = remove_prefix(string=signature, prefix=PROTOTYPE_PREFIX)
        function_name_has_wildcard: bool = signature is not None and signature.endswith(
            "*"
        )

        if file is not None:
            file_key: str = self._relativize_filepath_to_key(filepath=file)
            if file_key in self.table:
                functions = self.table[file_key]
            else:
                logging.debug(
                    f"Did not find any functions for {file} in lookup table, skip further querying"
                )
                return functions
        else:
            if (
                signature is not None
                and signature not in self.function_cache
                and not function_name_has_wildcard
            ):
                logging.debug(
                    f"Did not find function {signature} in lookup table, skip further querying"
                )
                return functions
            elif signature is not None and not function_name_has_wildcard:
                functions = self.function_cache[signature]
                logging.debug(
                    f"Found {signature} in lookup table, only querying across {len(functions)} functions"
                )
            else:
                functions = self.all_functions_ordered_by_id
                logging.debug(
                    f"Not able to narrow down considered functions, querying across all {len(functions)} functions"
                )

        query_parts: List[str] = []
        if function_name_has_wildcard:
            # in the case of a wildcard, we strip the wildcard character and match by substring
            raw_function_name: str = signature[:-1]
            query_parts.append(f"'{raw_function_name}' in func.signature")
        elif signature is not None:
            query_parts.append(f"func.signature == '{signature}'")
        if namespace is not None:
            if namespace == "*":
                query_parts.append("func.namespace is not None")
            elif namespace == "":
                query_parts.append("func.namespace is None")
            else:
                query_parts.append(f"func.namespace == '{namespace}'")
        if class_name is not None:
            if class_name == "*":
                query_parts.append("func.class_name is not None")
            elif class_name == "":
                query_parts.append("func.class_name is None")
            else:
                query_parts.append(f"func.class_name == '{class_name}'")
        if len(query_parts) > 0:
            query = " and ".join(query_parts)
            logging.debug(f"Search query to find function: {query}")
            functions = list(filter(lambda func: eval(query), functions))
        return functions.copy()

    def find_functions_by_line(
        self, file: Path, line: int
    ) -> Optional[List[CoveredFunction]]:
        file_key: str = self._relativize_filepath_to_key(file)
        if file_key not in self.table:
            return None
        enclosing_funcs: List[CoveredFunction] = []
        for func in self.table[file_key]:
            if func.start <= line <= func.end:
                enclosing_funcs.append(func)
        return enclosing_funcs

    def get_function_by_identifier(self, identifier: int) -> CoveredFunction:
        return self.all_functions_ordered_by_id[identifier]

    def find_or_add_functions(self, file: Path, line: int) -> List[CoveredFunction]:
        functions: Optional[List[CoveredFunction]] = self.find_functions_by_line(
            file=file, line=line
        )
        if functions is not None:
            return functions
        return self.add_functions_for_line(file=file, line=line)

    def add_functions_for_line(self, file: Path, line: int) -> List[CoveredFunction]:
        file_key: str = self._relativize_filepath_to_key(file)
        if file_key not in self.table:
            self.add_functions(file=file)
        functions: Optional[List[CoveredFunction]] = self.find_functions_by_line(
            file, line
        )
        if functions is None or len(functions) == 0:
            raise Exception(
                f"Covered line outside of defined functions found: {file}:{line}"
            )
        return functions

    def add_functions(self, file: Path) -> List[CoveredFunction]:
        file_key: str = self._relativize_filepath_to_key(file)
        assert (
            file_key not in self.table
        ), "File key already in function lookup table, should never add functions again"
        parser = CSourceCodeParser()
        functions: List[FunctionDefinition] = parser.get_functions(file=file)
        covered_functions: List[CoveredFunction] = []

        for function in functions:
            assert self.max_id > -1
            covered_functions.append(
                CoveredFunction(
                    identifier=self.max_id,
                    file=file_key,
                    signature=function.signature,
                    start=function.start_line,
                    end=function.end_line,
                    namespace=function.namespace,
                    class_name=function.class_name,
                    properties=function.properties,
                )
            )
            self.max_id += 1

        self.table[file_key] = covered_functions.copy()
        self.all_functions_ordered_by_id += covered_functions

        return covered_functions

    def __eq__(self, other: "FunctionLookupTable") -> bool:
        return dict_equals(self.table, other.table)


class AbstractTestTrace(ABC, SerializerMixin):
    def __init__(self, table: Optional[Dict[str, Set]] = None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if table is not None:
            self.table: Dict[str, Set] = table
        else:
            self.table: Dict[str, Set] = {}

    def __eq__(self, other) -> bool:
        return dict_equals(self.table, other.table)

    @abstractmethod
    def to_csv(self, file: Path, **kwargs) -> None:
        pass

    @classmethod
    @abstractmethod
    def from_csv(cls, file: Path, **kwargs):
        pass

    def select_tests(
        self, affected_entity_ids: Set
    ) -> Tuple[Set[str], Set[str], Dict[str, List[Any]]]:
        all_tests: Set[str] = set()
        included_tests: Set[str] = set()
        last_found_affected_module: str = ""
        last_found_affected_suite: str = ""
        selection_causes: Dict[str, List[Any]] = dict()
        for test_id in sorted(
            self.table.keys(),
            key=lambda t: t.replace(GLOBAL_TEST_SETUP, "*"),
        ):
            entities: Set = self.table[test_id]
            test_module, test_suite, test_case = from_test_id(test_id)
            if test_suite is not None and test_case is not None:
                if test_suite not in [GLOBAL_TEST_SETUP, "*"] and test_case != "*":
                    all_tests.add(test_id)
                affected_entities = affected_entity_ids & entities
                is_affected = len(affected_entities) > 0

                # For java, we only have test_ids of the format *!!!test_suite_name!!!*,
                # which makes selection way simpler: we only select test suites that are affected.
                if test_module == "*" and test_case == "*":
                    if is_affected:
                        included_tests.add(test_id)
                        selection_causes[test_id] = list(affected_entities)
                    all_tests.add(test_id)
                    continue

                # For GoogleTest, we have test_ids for global and test suite setup as well.
                # Here, we need to distinguish and select tests that are directly or indirectly affected.
                # Global test setup
                if is_affected and test_suite == GLOBAL_TEST_SETUP:
                    last_found_affected_module = test_module
                # Test suite setup
                elif is_affected and test_case == "*":
                    last_found_affected_suite = f"{test_module}{TEST_ID_SEP}{test_suite}"
                # Test case that is either
                # (1) directly affected
                # (2) affected by global test setup
                # (3) affected by suite setup
                elif (
                    is_affected
                    or (test_module == last_found_affected_module)
                    or (
                        f"{test_module}{TEST_ID_SEP}{test_suite}"
                        == last_found_affected_suite
                    )
                ):
                    included_tests.add(test_id)
                else:
                    continue
                # Note that this can lead to empty lists for test cases which are selected
                # due to global/test suite setup changes
                selection_causes[test_id] = list(affected_entities)

        excluded_tests: Set[str] = all_tests - included_tests
        return included_tests, excluded_tests, selection_causes


class TestFileTraces(AbstractTestTrace):
    """
    The test file traces are stored as a hash table of test identifiers mapped to a set of filepaths:

    {
        "testmodule": {"path/to/foo.txt"},
        "testmodule!!!TestSuite": {"path/to/bar.csv"},
        "testmodule!!!TestSuite!!!TestCase": {"path/to/baz.zip"},
        ...
    }
    """

    def __init__(
        self,
        table: Optional[Dict[str, Set[str]]] = None,
        root_dir: Optional[Path] = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(table, *args, **kwargs)
        self.root_dir = root_dir

    def to_csv(self, file: Path, **kwargs):
        with file.open("w+") as csv_file:
            for test_id, filepaths in self.table.items():
                test_module, test_suite, test_case = from_test_id(test_id)
                for filepath in filepaths:
                    # Note: If we were to do more sophisticated filepath matching,
                    # we would need to store relative paths to `self.root_dir` here.
                    csv_file.write(
                        f"{test_module}{CSV_SEP}"
                        f"{test_suite or ''}{CSV_SEP}"
                        f"{test_case or ''}{CSV_SEP}"
                        f"{filepath}"
                        f"\n"
                    )

    @classmethod
    def from_csv(cls, file: Path, **kwargs) -> "TestFileTraces":
        table: Dict[str, Set[str]] = {}
        with file.open("r") as csv_file:
            for line in csv_file:
                test_module, test_suite, test_case, filepath = line.strip().split(
                    CSV_SEP
                )
                assert test_module is not None and test_module != ""
                assert filepath is not None
                test_id: str = get_test_id(test_module, test_suite, test_case)
                if test_id not in table:
                    table[test_id] = set()
                table[test_id].add(filepath)
        return cls(table=table)

    def add_coverage(self, coverage: TestCoverage) -> None:
        test_id: str = get_test_id(
            coverage.test_module, coverage.test_suite, coverage.test_case
        )
        if test_id not in self.table:
            self.table[test_id] = set()
        for file in coverage.covered_files:
            self.table[test_id].add(file.name.__str__().lower())


class TestFunctionTraces(AbstractTestTrace):
    """
    The test function traces are stored as a hash table of test identifiers mapped to a set of function IDs:

    {
        "testmodule": {1,4},
        "testmodule!!TestSuite": {4},
        "testmodule!!TestSuite!!TestCase": {1,2,3,4},
        ...
    }
    """

    def __init__(
        self, table: Optional[Dict[str, Set[int]]] = None, *args, **kwargs
    ) -> None:
        super().__init__(table, *args, **kwargs)

    def to_csv(self, file: Path, test_lookup: Optional[Path] = None, **kwargs):
        test_ids: List[str] = []
        test_id_counter: int = 0
        with file.open("w+") as csv_file:
            for test_id, functions in self.table.items():
                if test_lookup is not None:
                    test_ids.append(test_id)
                    for function_id in functions:
                        csv_file.write(f"{test_id_counter}{CSV_SEP}{function_id}\n")
                    test_id_counter += 1
                else:
                    test_module, test_suite, test_case = from_test_id(test_id)
                    for function_id in functions:
                        csv_file.write(
                            f"{test_module}{CSV_SEP}"
                            f"{test_suite or ''}{CSV_SEP}"
                            f"{test_case or ''}{CSV_SEP}"
                            f"{function_id}"
                            f"\n"
                        )
        if test_lookup is not None:
            with test_lookup.open("w+") as csv_file:
                for idx, test_id in enumerate(test_ids):
                    csv_file.write(f"{idx}{CSV_SEP}{test_id}\n")

    @classmethod
    def from_csv(
        cls, file: Path, test_lookup: Optional[Path] = None, **kwargs
    ) -> "TestFunctionTraces":
        test_ids: List[str] = []
        if test_lookup is not None:
            with test_lookup.open("r") as csv_file:
                for line in csv_file:
                    test_id: str = line.strip().split(CSV_SEP)[-1]
                    test_ids.append(test_id)
        table: Dict[str, Set[int]] = {}
        with file.open("r") as csv_file:
            for line in csv_file:
                function_id: int
                test_id: str
                if test_lookup is None:
                    (
                        test_module,
                        test_suite,
                        test_case,
                        function_id,
                    ) = line.strip().split(CSV_SEP)
                    assert test_module is not None and test_module != ""
                    assert function_id is not None
                    function_id = int(function_id)
                    test_id: str = get_test_id(test_module, test_suite, test_case)
                else:
                    test_idx, function_id = line.strip().split(CSV_SEP)
                    assert test_idx is not None
                    assert function_id is not None
                    test_idx = int(test_idx)
                    function_id = int(function_id)
                    test_id = test_ids[test_idx]
                if test_id not in table:
                    table[test_id] = set()
                table[test_id].add(function_id)
        return cls(table=table)

    def add_test_function_dependency(
        self,
        test_module: str,
        test_suite: str,
        function: CoveredFunction,
        test_case: str = "",
    ) -> None:
        test_id: str = get_test_id(test_module, test_suite, test_case)
        if test_id not in self.table:
            self.table[test_id] = set()
        if function.identifier not in self.table[test_id]:
            self.table[test_id].add(function.identifier)


class CoverageParser:
    def __init__(
        self,
        extension: str,
        lookup_files: List[Path],
        java_mode: bool = False,
        regex: Optional[str] = None,
    ) -> None:
        self.extension: str = extension
        self.lookup_files = lookup_files
        self.test_identifier_lookup = {
            file.parent.name: self._extract_test_identifier_from_dump_lookup(
                lookup_file=file
            )
            for file in lookup_files
        }
        self.java_mode = java_mode
        self.regex: Optional[Pattern] = (
            re.compile(regex, flags=re.IGNORECASE) if regex is not None else None
        )

    @classmethod
    def _extract_test_identifier_from_dump_lookup(
        cls, lookup_file: Path
    ) -> Dict[str, str]:
        lookup: Dict[str, str] = {}
        for line in lookup_file.read_text().splitlines():
            if CSV_SEP in line:
                try:
                    line_fragments: List[str] = line.split(CSV_SEP)
                    lookup[line_fragments[0]] = line_fragments[1]
                except Exception as e:
                    logging.warning(
                        f"{e}: Failed to parse test identifier from dump lookup."
                    )
        return lookup

    def _extract_test_info_from_file(
        self,
        file: Path,
        test_module: Optional[str] = None,
        test_suite: Optional[str] = None,
        test_case: Optional[str] = None,
        test_result: Optional[str] = None,
    ) -> Tuple[str, str, str, Optional[str]]:
        """
        Extracts test module, test suite, test name, and test result from a coverage file
        By default, the test module, suite, and case identifiers are extracted by convention from the coverage file name
        and its parent directory name.
        """
        file_name_without_ext: str = file.name.split(self.extension)[0]
        if (
            file.parent.name not in self.test_identifier_lookup
            or file_name_without_ext
            not in self.test_identifier_lookup[file.parent.name]
        ) and not (test_suite or test_case):
            raise Exception("Failed to find test suite or test case information")
        test_identifier: str = self.test_identifier_lookup[file.parent.name][
            file_name_without_ext
        ]
        if not test_module:
            if self.java_mode:
                test_module = "*"  # in java, we do not have one binary (i.e., test module) per test
            else:
                test_module = file.parent.name
        if not test_suite:
            if self.java_mode:
                test_suite = test_identifier
            else:
                test_suite = test_identifier.split(TEST_SUITE_CASE_SEP)[0].split(
                    TEST_RESULT_SEP
                )[
                    0
                ]  # cut off __RESULT or __setup
        if (
            not test_case and TEST_SUITE_CASE_SEP not in test_identifier
        ) or self.java_mode:
            test_case = "*"
        elif not test_case and TEST_SUITE_CASE_SEP in test_identifier:
            test_case_with_result: str = test_identifier.split(TEST_SUITE_CASE_SEP)[1]
            test_case = test_case_with_result.split(TEST_RESULT_SEP)[0]
            test_result = test_case_with_result.split(TEST_RESULT_SEP)[1]
        return test_module, test_suite, test_case, test_result

    def parse_coverage(
        self,
        coverage_file: Path,
        test_module: Optional[str] = None,
        test_suite: Optional[str] = None,
        test_case: Optional[str] = None,
        test_result: Optional[str] = None,
    ) -> Optional[TestCoverage]:
        """
        Parses single coverage file that corresponds to a test entity (suite or case).
        """
        try:
            (
                test_module,
                test_suite,
                test_case,
                test_result,
            ) = self._extract_test_info_from_file(
                file=coverage_file,
                test_module=test_module,
                test_suite=test_suite,
                test_case=test_case,
                test_result=test_result,
            )
        except Exception as e:
            logging.warning(f"{e}: Failed to parse coverage from file {coverage_file}.")
            return None

        # exclude irrelevant parts of test execution
        if test_suite in ["BEFORE_PROGRAM_START"]:
            return None

        coverage: TestCoverage = TestCoverage(
            test_module=test_module,
            test_suite=test_suite,
            test_case=test_case,
            test_result=test_result,
            covered_lines=set(),
            covered_files=set(),
        )

        with coverage_file.open(mode="r") as file:
            for line in file:
                if "+0x" in line and ("\\" in line or "/" in line):
                    coverage_fragments: List[str] = (
                        line.split("+0x")[1].split("\n")[0].split(COVERAGE_SEP)
                    )
                    file_path: Path = Path(coverage_fragments[1])
                    if self.regex and not self.regex.match(file_path.__str__()):
                        continue
                    try:
                        symbol_name: str = coverage_fragments[2]
                        line_no: int = int(coverage_fragments[3])
                        covered_line: CoveredLine = CoveredLine(
                            file=file_path, symbol_name=symbol_name, line=line_no
                        )
                        coverage.covered_lines.add(covered_line)
                    except Exception as e:
                        logging.warning(
                            f"{e}: Failed to parse line {line} for coverage"
                        )

        return coverage

    def parse_syscalls(
        self,
        syscalls_file: Path,
        test_module: Optional[str] = None,
        test_suite: Optional[str] = None,
        test_case: Optional[str] = None,
        test_result: Optional[str] = None,
    ) -> Optional[TestCoverage]:
        """
        Parses single syscalls file that corresponds to a test entity (suite or case).
        """
        try:
            (
                test_module,
                test_suite,
                test_case,
                test_result,
            ) = self._extract_test_info_from_file(
                file=syscalls_file,
                test_module=test_module,
                test_suite=test_suite,
                test_case=test_case,
                test_result=test_result,
            )
        except Exception as e:
            logging.warning(f"{e}: Failed to parse syscalls from file {syscalls_file}.")
            return None

        # exclude irrelevant parts of test execution
        if test_suite in ["BEFORE_PROGRAM_START"]:
            return None

        coverage: TestCoverage = TestCoverage(
            test_module=test_module,
            test_suite=test_suite,
            test_case=test_case,
            test_result=test_result,
            covered_lines=set(),
            covered_files=set(),
        )

        with syscalls_file.open(mode="r") as file:
            for line in file:
                try:
                    file_path: Path = Path(
                        line.split("\n")[0]
                        .strip()
                        .replace("\\??\\", "")  # fix Win32 paths
                    ).resolve()
                    if self.regex and not self.regex.match(file_path.__str__()):
                        logging.debug(
                            f"File {file_path} did not match regex {self.regex.__str__()}, skipping."
                        )
                        continue
                    coverage.covered_files.add(file_path)
                except Exception as e:
                    logging.warning(f"{e}: Failed to parse accessed file {line}")
        return coverage


class SymbolResolver:
    def __init__(
        self,
        root: Path,
        ext: str,
        file_regex: str,
        symbol_resolver_executable: Path,
    ) -> None:
        self.root = root
        self.ext = ext
        self.file_regex = file_regex
        self.symbol_resolver_executable = symbol_resolver_executable

    def resolve_symbols(self) -> bool:
        has_failed: bool = False
        resolver_executable: Optional[str] = check_executable_exists(
            program=self.symbol_resolver_executable.resolve().__str__()
        )
        if resolver_executable:
            command: str = " ".join(
                [
                    f'"{resolver_executable}"',  # need the quotes to support paths with spaces
                    f"-debug",
                    f'-root "{self.root.resolve()}"',
                    f"-ext {self.ext}",
                    f'-regex "{self.file_regex}"',
                ]
            )
            process: sb.CompletedProcess = sb.run(
                command,
                text=True,
                capture_output=True,
                shell=True,
            )
            output: str = process.stdout + process.stderr
            logging.info(f"Exit code: {process.returncode} Output: {output}")
            if process.returncode != 0:
                has_failed = True
        return has_failed


def call_symbol_resolver(
    root: Path,
    extension: str,
    file_regex: str,
    symbol_resolver_executable: Path,
) -> None:
    """
    Use this function with multiprocessing (local functions cannot be pickled, hence, we need a global function).
    """
    logging.info(f"Starting new resolver process for root: {root}")
    resolver: SymbolResolver = SymbolResolver(
        root=root,
        ext=extension,
        file_regex=file_regex,
        symbol_resolver_executable=symbol_resolver_executable,
    )
    resolver.resolve_symbols()
