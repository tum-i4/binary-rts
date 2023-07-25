import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import List, Set, Optional, Dict

import typer

from binaryrts.commands.select import EXCLUDED_TESTS_FILE
from binaryrts.parser.conversion.base import CoverageFormat, CoverageConverter
from binaryrts.parser.conversion.lcov import LCOVCoverageConverter
from binaryrts.parser.conversion.sonar import SonarCoverageConverter
from binaryrts.parser.coverage import (
    FunctionLookupTable,
    TestFunctionTraces,
    TEST_LOOKUP_FILE,
)
from binaryrts.util.fs import has_ext

app = typer.Typer()


@app.callback()
def utils():
    """
    BinaryRTS utilities
    """
    pass


@app.command()
def merge(
    output: Path = typer.Option(
        lambda: Path(os.getcwd()),
        "-o",
        writable=True,
        exists=False,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    include_files: List[Path] = typer.Option(
        [],
        "--include",
        help="A list of `included.txt` files that ought to be merged.",
    ),
    exclude_files: List[Path] = typer.Option(
        [],
        "--exclude",
        help="A list of `excluded.txt` files that ought to be merged.",
    ),
):
    """
    Merges includes and excludes files into a single excludes file that can be used for RTS.
    """
    final_excludes: Set[str] = set()
    for file in exclude_files:
        with file.open("r") as fp:
            for line in fp:
                test_id: str = line.strip()
                if len(test_id) > 0:
                    final_excludes.add(test_id)
    for file in include_files:
        with file.open("r") as fp:
            for line in fp:
                test_id: str = line.strip()
                if test_id == "*":
                    final_excludes = set()
                    break
                if len(test_id) > 0 and test_id in final_excludes:
                    final_excludes.remove(test_id)
    output.mkdir(parents=True, exist_ok=True)
    (output / EXCLUDED_TESTS_FILE).write_text("\n".join(final_excludes))


@app.command()
def coverage(
    function_lookup_file: Path = typer.Option(
        ...,
        "--lookup",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    test_function_traces_file: Path = typer.Option(
        ...,
        "--traces",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    output: Path = typer.Option(
        lambda: Path(os.getcwd()),
        "-o",
        writable=True,
        exists=False,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    root_dir: Optional[Path] = typer.Option(
        None,
        "--repo",
        writable=True,
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Root directory which is used to resolve file paths.",
    ),
    coverage_format: CoverageFormat = typer.Option(
        CoverageFormat.LCOV, "--format", "-f"
    ),
):
    """
    Convert the test traces into a coverage format to be used by a coverage conversion tool.
    """
    logging.info(f"Loading function table from {function_lookup_file}")
    function_lookup_table: FunctionLookupTable
    if has_ext(function_lookup_file, exts=[".csv"]):
        function_lookup_table = FunctionLookupTable.from_csv(
            function_lookup_file, root_dir=root_dir
        )
    elif has_ext(function_lookup_file, exts=[".pkl"]):
        function_lookup_table = FunctionLookupTable.from_pickle(function_lookup_file)
        function_lookup_table.root_dir = root_dir
    else:
        raise Exception(
            "Provided invalid function lookup file format, only .csv and .pkl are currently supported."
        )

    logging.info(f"Loading test function traces from {test_function_traces_file}")
    test_function_traces: TestFunctionTraces
    if has_ext(test_function_traces_file, exts=[".csv"]):
        test_function_traces = TestFunctionTraces.from_csv(
            test_function_traces_file,
            (test_function_traces_file.parent / TEST_LOOKUP_FILE)
            if (test_function_traces_file.parent / TEST_LOOKUP_FILE).exists()
            else None,
        )
    elif has_ext(test_function_traces_file, exts=[".pkl"]):
        test_function_traces = TestFunctionTraces.from_pickle(test_function_traces_file)
    else:
        raise Exception(
            "Provided invalid test traces file format, only .csv and .pkl are currently supported."
        )

    logging.info(f"Starting to convert coverage to format {coverage_format}.")
    converter: CoverageConverter
    if coverage_format == CoverageFormat.LCOV:
        converter = LCOVCoverageConverter(
            test_traces=test_function_traces, lookup=function_lookup_table
        )
    elif coverage_format == CoverageFormat.SONAR:
        converter = SonarCoverageConverter(
            test_traces=test_function_traces, lookup=function_lookup_table
        )
    else:
        raise Exception(f"Provided invalid coverage format {coverage_format}.")
    coverage_data: str = converter.convert()
    output.mkdir(parents=True, exist_ok=True)
    output_file: Path = output / converter.OUTPUT_FILE
    logging.info(f"Storing coverage to {output_file}.")
    output_file.write_text(coverage_data)


@app.command()
def compare_traces(
    old_function_lookup_file: Path = typer.Option(
        ...,
        "--old-lookup",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    old_test_function_traces_file: Path = typer.Option(
        ...,
        "--old-traces",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    new_function_lookup_file: Path = typer.Option(
        ...,
        "--new-lookup",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    new_test_function_traces_file: Path = typer.Option(
        ...,
        "--new-traces",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    output: Path = typer.Option(
        lambda: Path(os.getcwd()),
        "-o",
        writable=True,
        exists=False,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
):
    """Compare two test traces and lookup files."""
    old_function_lookup_table: FunctionLookupTable
    if has_ext(old_function_lookup_file, exts=[".csv"]):
        old_function_lookup_table = FunctionLookupTable.from_csv(
            old_function_lookup_file
        )
    elif has_ext(old_function_lookup_file, exts=[".pkl"]):
        old_function_lookup_table = FunctionLookupTable.from_pickle(
            old_function_lookup_file
        )
    else:
        raise Exception(
            "Provided invalid function lookup file format, only .csv and .pkl are currently supported."
        )
    new_function_lookup_table: FunctionLookupTable
    if has_ext(new_function_lookup_file, exts=[".csv"]):
        new_function_lookup_table = FunctionLookupTable.from_csv(
            new_function_lookup_file
        )
    elif has_ext(new_function_lookup_file, exts=[".pkl"]):
        new_function_lookup_table = FunctionLookupTable.from_pickle(
            new_function_lookup_file
        )
    else:
        raise Exception(
            "Provided invalid function lookup file format, only .csv and .pkl are currently supported."
        )

    old_test_function_traces: TestFunctionTraces
    if has_ext(old_test_function_traces_file, exts=[".csv"]):
        old_test_function_traces = TestFunctionTraces.from_csv(
            old_test_function_traces_file,
            (old_test_function_traces_file.parent / TEST_LOOKUP_FILE)
            if (old_test_function_traces_file.parent / TEST_LOOKUP_FILE).exists()
            else None,
        )
    elif has_ext(old_test_function_traces_file, exts=[".pkl"]):
        old_test_function_traces = TestFunctionTraces.from_pickle(
            old_test_function_traces_file
        )
    else:
        raise Exception(
            "Provided invalid test traces file format, only .csv and .pkl are currently supported."
        )
    new_test_function_traces: TestFunctionTraces
    if has_ext(new_test_function_traces_file, exts=[".csv"]):
        new_test_function_traces = TestFunctionTraces.from_csv(
            new_test_function_traces_file,
            (new_test_function_traces_file.parent / TEST_LOOKUP_FILE)
            if (new_test_function_traces_file.parent / TEST_LOOKUP_FILE).exists()
            else None,
        )
    elif has_ext(new_test_function_traces_file, exts=[".pkl"]):
        new_test_function_traces = TestFunctionTraces.from_pickle(
            new_test_function_traces_file
        )
    else:
        raise Exception(
            "Provided invalid test traces file format, only .csv and .pkl are currently supported."
        )

    missing_functions: Dict[str, List[str]] = defaultdict(list)
    total_old_func_names: Set[str] = set()
    for test, function_ids in old_test_function_traces.table.items():
        old_func_names: Set[str] = {
            old_function_lookup_table.get_function_by_identifier(func_id).full_name
            for func_id in function_ids
        }
        total_old_func_names |= old_func_names
        if test not in new_test_function_traces.table:
            missing_functions[test] = list(old_func_names)
            continue
        new_func_names: Set[str] = {
            new_function_lookup_table.get_function_by_identifier(func_id).full_name
            for func_id in new_test_function_traces.table[test]
        }
        diff: Set[str] = old_func_names - new_func_names
        if len(diff) > 0:
            missing_functions[test] = list(diff)

    logging.info(f"Missing functions in {len(missing_functions.keys())} tests.")
    logging.info(
        f"Number of distinct missing functions: {len(set(sum(missing_functions.values(), [])))} "
        f"of {len(total_old_func_names)} total functions."
    )
    output_file: Path = output / "diff.json"
    logging.info(
        f"Writing missing functions to file {output_file}"
    )
    output_file.write_text(f"{missing_functions}")

