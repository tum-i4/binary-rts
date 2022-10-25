from pathlib import Path
from typing import Optional, Iterable, Tuple, List, Dict

from binaryrts.parser.sourcecode import (
    FunctionDefinition,
    CSourceCodeParser,
    NonFunctionalEntityDefinition,
)


class CodeDiffAnalyzer:
    def __init__(
        self,
        parser: CSourceCodeParser,
        scope_analysis: bool = False,
        overload_analysis: bool = False,
        virtual_analysis: bool = False
    ) -> None:
        self.parser = parser
        self.function_cache: Dict[Path, List[FunctionDefinition]] = {}
        self.scope_analysis = scope_analysis
        self.overload_analysis = overload_analysis
        self.virtual_analysis = virtual_analysis

    def _get_functions(self, file: Path) -> List[FunctionDefinition]:
        filepath: Path = file.absolute()
        if filepath in self.function_cache:
            return self.function_cache[filepath]
        functions: List[FunctionDefinition] = self.parser.get_functions(file=file)
        self.function_cache[filepath] = functions
        return functions

    def get_changed_or_newly_overridden_functions(
        self, old_revision: Path, new_revision: Path
    ) -> Iterable[Tuple[FunctionDefinition, Optional[Path]]]:
        old_functions: List[FunctionDefinition] = self._get_functions(file=old_revision)
        new_functions: List[FunctionDefinition] = self._get_functions(file=new_revision)
        # (1) find all modified functions
        for new_func in new_functions:
            found: bool = False
            new_function_string: str = self.parser.get_raw_code(
                file=new_revision,
                start=new_func.start_line,
                end=new_func.end_line,
            )
            for old_func in old_functions:
                if new_func.identifier == old_func.identifier:
                    old_function_string: str = self.parser.get_raw_code(
                        file=old_revision,
                        start=old_func.start_line,
                        end=old_func.end_line,
                    )
                    if (
                        not new_func.is_prototype
                        and new_function_string != old_function_string
                    ):
                        yield new_func, new_revision
                    elif (
                        new_func.is_prototype
                        and new_function_string != old_function_string
                    ):
                        # this covers the case where a "virtual" or "override" keyword is added to an existing
                        # function prototype; this case is handled by (3) then
                        break
                    found = True
                    break

            # (2) find newly added functions that may override a function with similar name;
            # E.g., if type `B` extends `A` and `void foo(A& a)` exists, adding `void foo(B& b)` will
            # lead to the new function being called for objects of type `B`.
            if (
                self.overload_analysis
                and not found
                and not new_func.is_prototype
                and new_func.has_parameters
                and not new_func.is_test_function
            ):
                tmp_func: FunctionDefinition = FunctionDefinition(
                    file=new_func.file,
                    signature=new_func.raw_function_name
                    + "*",  # remove signature and add wildcard '*' char
                    start_line=new_func.start_line,
                    end_line=new_func.end_line,
                    class_name=None,
                    namespace=None,
                    properties=new_func.properties,
                )
                # this will query only by function name wildcard and disregard class or namespace
                # since this could potentially lead to many functions being marked as affected,
                # such as setter functions like `setName(...)`,
                # we limit this analysis to the current file, by returning `new_revision`
                yield tmp_func, new_revision

            # (3) find newly added "virtual"/"override" functions
            if (
                self.virtual_analysis
                and not found
                and new_func.properties
                and (
                    "virtual" in new_func.properties
                    or "override" in new_func.properties
                )
            ):
                tmp_func: FunctionDefinition = FunctionDefinition(
                    file=new_func.file,
                    signature=new_func.signature,
                    class_name="*",  # this will cause to find all functions with *any* class
                    start_line=new_func.start_line,
                    end_line=new_func.end_line,
                    namespace=None,
                    properties=new_func.properties,
                )
                yield tmp_func, None

            # (4) find newly added member or namespace local functions that may override a function from an outer scope
            # Note: Use with care; this can be expensive, as all functions with the same name are marked as affected.
            elif (
                self.scope_analysis
                and not found
                and (new_func.class_name is not None or new_func.namespace is not None)
                and not new_func.is_prototype
            ):
                tmp_func: FunctionDefinition = FunctionDefinition(
                    file=new_func.file,
                    signature=new_func.signature,
                    start_line=new_func.start_line,
                    end_line=new_func.end_line,
                    class_name=None,
                    namespace=None,
                    properties=new_func.properties,
                )
                # this will query only by function name and disregard class or namespace
                yield tmp_func, None

    def get_deleted_functions(
        self, old_revision: Path, new_revision: Path
    ) -> Iterable[Tuple[FunctionDefinition, Optional[Path]]]:
        # find all deleted/renamed functions
        old_functions: List[FunctionDefinition] = self._get_functions(file=old_revision)
        new_functions: List[FunctionDefinition] = self._get_functions(file=new_revision)

        for old_func in old_functions:
            found: bool = False
            for new_func in new_functions:
                if old_func.identifier == new_func.identifier:
                    found = True
                    break
            if not found:
                yield old_func, new_revision

    def get_changed_non_functional_entities(
        self, old_revision: Path, new_revision: Path
    ) -> Iterable[Tuple[NonFunctionalEntityDefinition, Optional[Path]]]:
        old_non_functionals: List[
            NonFunctionalEntityDefinition
        ] = self.parser.get_non_functional_entities(file=old_revision)
        new_non_functionals: List[
            NonFunctionalEntityDefinition
        ] = self.parser.get_non_functional_entities(file=new_revision)

        for new_non_func in new_non_functionals:
            found: bool = False
            new_code_string: str = self.parser.get_raw_code(
                file=new_revision,
                start=new_non_func.start_line,
                end=new_non_func.end_line,
            )
            for old_non_func in old_non_functionals:
                if new_non_func.name == old_non_func.name:
                    old_code_string: str = self.parser.get_raw_code(
                        file=old_revision,
                        start=old_non_func.start_line,
                        end=old_non_func.end_line,
                    )
                    # modified non-functionals
                    if new_code_string != old_code_string:
                        yield new_non_func, new_revision
                    found = True
                    break

            # added non-functionals
            if not found:
                yield new_non_func, new_revision

        # deleted non-functionals
        for old_non_func in old_non_functionals:
            found: bool = False
            for new_non_func in new_non_functionals:
                if old_non_func.name == new_non_func.name:
                    found = True
                    break
            if not found:
                yield old_non_func, new_revision
