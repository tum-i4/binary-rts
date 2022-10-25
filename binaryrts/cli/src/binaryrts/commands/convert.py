import logging
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set, Tuple

import numpy as np
import typer

from binaryrts.parser.coverage import (
    TestCoverage,
    CoverageParser,
    FunctionLookupTable,
    TestFunctionTraces,
    CoveredFunction,
    TestFileTraces,
    call_symbol_resolver,
    FUNCTION_LOOKUP_FILE,
    TEST_FUNCTION_TRACES_FILE,
    TEST_LOOKUP_FILE,
    TEST_FILE_TRACES_FILE,
    PICKLE_TEST_FUNCTION_TRACES_FILE,
    PICKLE_FUNCTION_LOOKUP_FILE,
    PICKLE_TEST_FILE_TRACES_FILE,
)
from binaryrts.util.fs import delete_files
from binaryrts.util.mp import run_with_multi_processing

app = typer.Typer()

random.seed(42)


@dataclass
class ConvertCommonOptions:
    output_dir: Path
    input_dir: Path
    regex: str
    lookup_file_name: str
    clean: bool
    n_processes: int
    binary_output: bool
    repo_root_dir: Optional[Path] = field(default=None)


@app.callback()
def convert(
    ctx: typer.Context,
    input_dir: Path = typer.Option(
        lambda: Path(os.getcwd()),
        "--input",
        "-i",
        writable=True,
        exists=False,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Root directory where to search for coverage files.",
    ),
    output_dir: Path = typer.Option(
        lambda: Path(os.getcwd()),
        "--output",
        "-o",
        writable=True,
        exists=False,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    regex: str = typer.Option(
        default=".*", help="Regular expression to filter covered files in test traces."
    ),
    lookup_file_name: str = typer.Option(
        "dump-lookup.log", "--lookup", help="Name of dump lookup file."
    ),
    repo_root_dir: Optional[Path] = typer.Option(
        None,
        "--repo",
        writable=True,
        exists=False,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Repository root directory; if provided, all files in the traces will be relative to this directory.",
    ),
    clean: bool = typer.Option(False),
    n_processes: int = typer.Option(
        1,
        "--processes",
        help="Number of processes for parallelization.",
    ),
    binary_output: bool = typer.Option(
        False,
        "--binary",
        "--pickle",
        help="Enables binary output using Python's (unsafe) pickle format.",
    ),
):
    """
    Convert test traces
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    ctx.obj = ConvertCommonOptions(
        input_dir=input_dir,
        output_dir=output_dir,
        regex=regex,
        lookup_file_name=lookup_file_name,
        clean=clean,
        n_processes=n_processes,
        repo_root_dir=repo_root_dir,
        binary_output=binary_output,
    )


def _filter_and_sort_coverage_files(
    root: Path, extension: str, lookup_file_name: str
) -> List[Path]:
    # By default, the BinaryRTS listener and client dump coverage after test suite execution,
    # which will be discarded here.
    return sorted(
        [
            file
            for file in root.glob(f"**/*{extension}")
            if file.name
            not in [
                lookup_file_name,
                f"coverage{extension}",
            ]
        ],
        reverse=True,
    )


def _parse_coverage_files(
    coverage_files: List[Path], parser: CoverageParser, parse_syscalls: bool = False
) -> List[TestCoverage]:
    logging.warning(f"Worker parsing {len(coverage_files)} coverage files...")
    test_coverage: List[TestCoverage] = []
    for file in coverage_files:
        if parse_syscalls:
            coverage: Optional[TestCoverage] = parser.parse_syscalls(syscalls_file=file)
        else:
            coverage: Optional[TestCoverage] = parser.parse_coverage(coverage_file=file)
        if coverage:
            test_coverage.append(coverage)
        else:
            logging.debug(f"Failed to parse coverage from {file}")
    logging.warning(
        f"Worker done parsing {len(coverage_files)}, found {len(test_coverage)} valid test coverage dumps."
    )
    return test_coverage


@app.command()
def cpp(
    ctx: typer.Context,
    extension: str = typer.Option(
        ".log", "-e", "--ext", help="Coverage file extension to search for recursively."
    ),
    java_mode: bool = typer.Option(
        False,
        "--java",
        help="Whether to analyze coverage from java tests (one coverage file per test suite, no test modules here).",
    ),
    resolve_symbols: bool = typer.Option(
        False,
        "--symbols",
        help="Whether to resolve symbols. Necessary if raw BB offsets have been dumped by BinaryRTS DR client.",
    ),
    symbol_resolver_executable: Optional[Path] = typer.Option(
        None,
        "--resolver",
        exists=False,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
        help="Path to BinaryRTS resolver binary (requires dbghelp.dll and dynamorio.dll at the same location).",
    ),
    create_test_lookup: bool = typer.Option(
        True,
        "--test-lookup",
        help="Whether to create a test lookup file (by default, one will be created) "
        "or store the test information inside the test traces.",
    ),
):
    """
    Convert raw BB coverage into structured test traces and function lookup tables.
    Users can provide an input directory, which will be recursively searched for coverage files.
    We expect the directory name where a coverage file is located to be the name of the surrounding module.
    E.g., if we have directory structure as follows:

        \b
        module_a
            1.log
            2.log
            3.log
            dump-lookup.log
        module_b
            1.log
            dump-lookup.log

    We will simply use the directory names `module_a` and `module_b` as the identifiers for the surrounding modules.
    """
    if resolve_symbols and (
        symbol_resolver_executable is None or not symbol_resolver_executable.exists()
    ):
        raise Exception(
            f"Could not find symbol resolver executable at {symbol_resolver_executable}."
        )

    opts: ConvertCommonOptions = ctx.obj
    parser: CoverageParser = CoverageParser(
        extension=extension,
        lookup_files=[
            file for file in sorted(opts.input_dir.glob(f"**/{opts.lookup_file_name}"))
        ],
        regex=opts.regex
        if not resolve_symbols
        else None,  # the regex is passed to the resolver anyways...
        java_mode=java_mode,
    )

    all_coverage_files: List[Path] = _filter_and_sort_coverage_files(
        opts.input_dir, extension=extension, lookup_file_name=opts.lookup_file_name
    )

    # in case we need to resolve symbols, we can parallelize if desired
    if resolve_symbols and symbol_resolver_executable.exists():
        if opts.n_processes > 1:
            coverage_dirs: Set[Path] = {
                coverage_file.parent for coverage_file in all_coverage_files
            }
            mp_iterable: List[Tuple[Path, str, str, Path]] = [
                (p, extension, opts.regex, symbol_resolver_executable)
                for p in coverage_dirs
            ]
            run_with_multi_processing(
                func=call_symbol_resolver,
                iterable=mp_iterable,
                n_cpu=opts.n_processes,
            )
        else:
            call_symbol_resolver(
                root=opts.input_dir,
                extension=extension,
                file_regex=opts.regex,
                symbol_resolver_executable=symbol_resolver_executable,
            )

    all_test_coverage: List[TestCoverage]
    if opts.n_processes > 1:
        logging.info(
            f"Starting {opts.n_processes} processes for {len(all_coverage_files)} paths."
        )
        # in the case of multi-processing, we shuffle for at least random distribution of large coverage files
        random.shuffle(all_coverage_files)
        per_dir_coverage: List[List[TestCoverage]] = run_with_multi_processing(
            func=_parse_coverage_files,
            iterable=[
                (
                    coverage_files,
                    parser,
                    False,
                )
                for coverage_files in np.array_split(
                    all_coverage_files, opts.n_processes
                )
                if len(coverage_files) > 0
            ],
            n_cpu=opts.n_processes,
        )
        logging.info(
            f"Parsed {len(per_dir_coverage)} coverage dumps, aggregating to total coverage."
        )
        all_test_coverage = sum(per_dir_coverage, [])
    else:
        all_test_coverage = _parse_coverage_files(
            coverage_files=all_coverage_files,
            parser=parser,
            parse_syscalls=False,
        )

    logging.info(
        "Done with collecting and parsing coverage files, starting to construct traces."
    )
    # create function test traces and function lookups
    function_lookup_table: FunctionLookupTable = FunctionLookupTable(
        root_dir=opts.repo_root_dir
    )
    test_function_traces: TestFunctionTraces = TestFunctionTraces()
    for idx, test_coverage in enumerate(all_test_coverage):
        logging.debug(
            f"Adding coverage ({idx + 1}/{len(all_test_coverage)}): "
            f"{test_coverage.test_module}:"
            f"{test_coverage.test_suite}:"
            f"{test_coverage.test_case}"
        )
        # TODO: we could check here, if the test result was PASSED and only add the trace then.
        for covered_line in test_coverage.covered_lines:
            try:
                functions: List[
                    CoveredFunction
                ] = function_lookup_table.find_or_add_functions(
                    file=covered_line.file, line=covered_line.line
                )
                for func in functions:
                    test_function_traces.add_test_function_dependency(
                        test_module=test_coverage.test_module,
                        test_suite=test_coverage.test_suite,
                        test_case=test_coverage.test_case,
                        function=func,
                    )
            except Exception as e:
                logging.debug(e)
                logging.debug(
                    f"Exception when looking up {covered_line.file}->{covered_line.symbol_name}->{covered_line.line} in "
                    f"{test_coverage.test_module}:{test_coverage.test_suite}:{test_coverage.test_case}"
                )

    if opts.binary_output:
        function_lookup_table.to_pickle(opts.output_dir / PICKLE_FUNCTION_LOOKUP_FILE)
        test_function_traces.to_pickle(
            opts.output_dir / PICKLE_TEST_FUNCTION_TRACES_FILE
        )
    else:
        function_lookup_table.to_csv(opts.output_dir / FUNCTION_LOOKUP_FILE)
        test_function_traces.to_csv(
            opts.output_dir / TEST_FUNCTION_TRACES_FILE,
            test_lookup=(opts.output_dir / TEST_LOOKUP_FILE)
            if create_test_lookup
            else None,
        )

    # clean files
    if opts.clean:
        delete_files(opts.input_dir.glob(f"**/*{extension}"))


@app.command()
def syscalls(
    ctx: typer.Context,
    extension: str = typer.Option(
        ".log.syscalls", "-e", "--ext", help="File extension to search for recursively."
    ),
):
    """
    Convert raw opened files traced via syscall analysis into structured test traces and file lookup tables.
    """
    opts: ConvertCommonOptions = ctx.obj
    parser: CoverageParser = CoverageParser(
        regex=opts.regex,
        extension=extension,
        lookup_files=[
            file for file in sorted(opts.input_dir.glob(f"**/{opts.lookup_file_name}"))
        ],
    )

    all_coverage_files: List[Path] = _filter_and_sort_coverage_files(
        opts.input_dir, extension=extension, lookup_file_name=opts.lookup_file_name
    )

    all_test_coverage: List[TestCoverage]
    if opts.n_processes > 1:
        # in the case of multi-processing, we shuffle for at least random distribution of large coverage files
        random.shuffle(all_coverage_files)
        per_dir_coverage: List[List[TestCoverage]] = run_with_multi_processing(
            func=_parse_coverage_files,
            iterable=[
                (
                    coverage_files,
                    parser,
                    True,
                )
                for coverage_files in np.array_split(
                    all_coverage_files, opts.n_processes
                )
                if len(coverage_files) > 0
            ],
            n_cpu=opts.n_processes,
        )
        all_test_coverage = sum(per_dir_coverage, [])
    else:
        all_test_coverage = _parse_coverage_files(
            coverage_files=all_coverage_files,
            parser=parser,
            parse_syscalls=True,
        )

    logging.info(
        "Done with collecting and parsing syscall files, starting to construct traces."
    )

    # create file-level per-test traces
    test_file_traces: TestFileTraces = TestFileTraces(root_dir=opts.repo_root_dir)
    for coverage in all_test_coverage:
        test_file_traces.add_coverage(coverage)

    if opts.binary_output:
        test_file_traces.to_pickle(opts.output_dir / PICKLE_TEST_FILE_TRACES_FILE)
    else:
        test_file_traces.to_csv(opts.output_dir / TEST_FILE_TRACES_FILE)

    # clean files
    if opts.clean:
        delete_files(opts.input_dir.glob(f"**/*{extension}"))
