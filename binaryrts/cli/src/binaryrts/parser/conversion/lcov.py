from dataclasses import dataclass
from typing import List, Set

from binaryrts.parser.coverage import TestFunctionTraces, FunctionLookupTable, CoveredFunction
from binaryrts.parser.conversion.base import CoverageConverter

class LCOVCoverageConverter(CoverageConverter):

    OUTPUT_FILE: str = "coverage.info"

    def __init__(
        self, test_traces: TestFunctionTraces, lookup: FunctionLookupTable, include_functions: bool = False
    ) -> None:
        super().__init__()
        self.test_traces = test_traces
        self.lookup = lookup
        self.include_functions = include_functions

    def convert(self) -> str:
        lines: List[str] = []
        covered_function_ids: Set[int] = set()
        for covered_funcs in self.test_traces.table.values():
            covered_function_ids |= covered_funcs

        for file, funcs in self.lookup.table.items():
            # SF:<filepath>
            lines.append(f"SF:{file}")
            covered_funcs: List[CoveredFunction] = []
            uncovered_funcs: List[CoveredFunction] = []
            for func in funcs:
                if self.include_functions:
                    # FN:<line number of function start>,<function name>
                    lines.append(f"FN:{func.start},{func.signature.replace(',','')}")
                if func.identifier in covered_function_ids:
                    covered_funcs.append(func)
                else:
                    uncovered_funcs.append(func)
            if self.include_functions:
                for func in covered_funcs:
                    # FNDA:<hit count>,<function name>
                    lines.append(f"FNDA:1,{func.signature.replace(',','')}")
            for func in covered_funcs:
                # DA:<line number>,<hit count>
                for line in range(func.start, func.end + 1):
                    lines.append(f"DA:{line},1")
            for func in uncovered_funcs:
                # DA:<line number>,<hit count>
                for line in range(func.start, func.end + 1):
                    lines.append(f"DA:{line},0")
            lines.append("end_of_record")
        return "\n".join(lines)