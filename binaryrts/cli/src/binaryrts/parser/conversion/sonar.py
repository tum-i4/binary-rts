from typing import List, Set

from binaryrts.parser.conversion.base import CoverageConverter
from binaryrts.parser.coverage import (
    TestFunctionTraces,
    FunctionLookupTable,
    CoveredFunction,
)


class SonarCoverageConverter(CoverageConverter):
    OUTPUT_FILE: str = "coverage.xml"

    def __init__(
        self, test_traces: TestFunctionTraces, lookup: FunctionLookupTable
    ) -> None:
        super().__init__()
        self.test_traces = test_traces
        self.lookup = lookup

    def convert(self) -> str:
        lines: List[str] = []
        covered_function_ids: Set[int] = set()
        for covered_funcs in self.test_traces.table.values():
            covered_function_ids |= covered_funcs
        lines.append('<coverage version="1">')
        for file, funcs in self.lookup.table.items():
            # <file path="<filepath>">
            lines.append(f'\t<file path="{file}">')
            covered_funcs: List[CoveredFunction] = []
            uncovered_funcs: List[CoveredFunction] = []
            for func in funcs:
                if func.identifier in covered_function_ids:
                    covered_funcs.append(func)
                else:
                    uncovered_funcs.append(func)
            for func in covered_funcs:
                # <lineToCover lineNumber="15" covered="true"/>
                for line in range(func.start, func.end + 1):
                    lines.append(f'\t\t<lineToCover lineNumber="{line}" covered="true"/>')
            for func in uncovered_funcs:
                # <lineToCover lineNumber="15" covered="false"/>
                for line in range(func.start, func.end + 1):
                    lines.append(f'\t\t<lineToCover lineNumber="{line}" covered="false"/>')
            lines.append("\t</file>")
        lines.append("</coverage>")
        return "\n".join(lines)
