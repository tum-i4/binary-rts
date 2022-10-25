import os
import unittest
from pathlib import Path
from typing import List

from binaryrts.parser.sourcecode import CSourceCodeParser, FunctionDefinition
from binaryrts.rts.diff import CodeDiffAnalyzer

RESOURCES_DIR: Path = Path(os.path.dirname(__file__)) / "resources"


class CodeDiffAnalyzerTestCase(unittest.TestCase):
    def test_changed_function(self):
        old_revision: Path = RESOURCES_DIR / "diff" / "operator_v1.cpp"
        new_revision: Path = RESOURCES_DIR / "diff" / "operator_v2.cpp"
        analyzer = CodeDiffAnalyzer(parser=CSourceCodeParser())
        changed_functions: List[FunctionDefinition] = [
            func
            for func, file in analyzer.get_changed_or_newly_overridden_functions(
                old_revision=old_revision, new_revision=new_revision
            )
        ]

        self.assertListEqual(
            [
                FunctionDefinition(
                    file=new_revision,
                    class_name="BigInteger",
                    signature="operator ==(BigIntegerconst&val))",
                    properties="const",
                    start_line=55,
                    end_line=59,
                    namespace=None,
                ),
            ],
            changed_functions,
        )

    def test_added_override_virtual_function_without_analysis(self):
        old_revision: Path = RESOURCES_DIR / "diff" / "override_v1.cpp"
        new_revision: Path = RESOURCES_DIR / "diff" / "override_v2.cpp"
        analyzer = CodeDiffAnalyzer(parser=CSourceCodeParser(), virtual_analysis=False)
        changed_functions: List[FunctionDefinition] = [
            func
            for func, file in analyzer.get_changed_or_newly_overridden_functions(
                old_revision=old_revision, new_revision=new_revision
            )
        ]

        self.assertListEqual(
            [],
            changed_functions,
        )

    def test_added_override_virtual_function(self):
        old_revision: Path = RESOURCES_DIR / "diff" / "override_v1.cpp"
        new_revision: Path = RESOURCES_DIR / "diff" / "override_v2.cpp"
        analyzer = CodeDiffAnalyzer(parser=CSourceCodeParser(), virtual_analysis=True)
        changed_functions: List[FunctionDefinition] = [
            func
            for func, file in analyzer.get_changed_or_newly_overridden_functions(
                old_revision=old_revision, new_revision=new_revision
            )
        ]

        self.assertListEqual(
            [
                FunctionDefinition(
                    file=new_revision,
                    signature="foobar(a::b&baz))",
                    start_line=3,
                    end_line=3,
                    namespace=None,
                    class_name="*",
                    properties="const,override,virtual",
                ),
            ],
            changed_functions,
        )

    def test_added_override_function_with_overload(self):
        old_revision: Path = RESOURCES_DIR / "diff" / "override_v1.cpp"
        new_revision: Path = RESOURCES_DIR / "diff" / "override_v2.cpp"
        analyzer = CodeDiffAnalyzer(parser=CSourceCodeParser(), overload_analysis=True)
        changed_functions: List[FunctionDefinition] = [
            func
            for func, file in analyzer.get_changed_or_newly_overridden_functions(
                old_revision=old_revision, new_revision=new_revision
            )
        ]

        self.assertListEqual(
            [
                FunctionDefinition(
                    file=new_revision,
                    signature="foobar*",
                    start_line=3,
                    end_line=3,
                    namespace=None,
                    class_name=None,
                    properties="const,override,virtual",
                ),
            ],
            changed_functions,
        )

    def test_added_override_function_with_overload_and_scope_and_virtual_analysis(self):
        old_revision: Path = RESOURCES_DIR / "diff" / "override_v1.cpp"
        new_revision: Path = RESOURCES_DIR / "diff" / "override_v2.cpp"
        analyzer = CodeDiffAnalyzer(
            parser=CSourceCodeParser(),
            overload_analysis=True,
            scope_analysis=True,
            virtual_analysis=True,
        )
        changed_functions: List[FunctionDefinition] = [
            func
            for func, file in analyzer.get_changed_or_newly_overridden_functions(
                old_revision=old_revision, new_revision=new_revision
            )
        ]

        self.assertListEqual(
            [
                FunctionDefinition(
                    file=new_revision,
                    signature="foo()",
                    start_line=5,
                    end_line=5,
                    namespace=None,
                    class_name=None,
                ),
                FunctionDefinition(
                    file=new_revision,
                    signature="foobar*",
                    start_line=3,
                    end_line=3,
                    namespace=None,
                    class_name=None,
                    properties="const,override,virtual",
                ),
                FunctionDefinition(
                    file=new_revision,
                    signature="foobar(a::b&baz))",
                    start_line=3,
                    end_line=3,
                    namespace=None,
                    class_name="*",
                    properties="const,override,virtual",
                ),
            ],
            changed_functions,
        )

    def test_added_overload_function(self):
        old_revision: Path = RESOURCES_DIR / "diff" / "overload_v1.cpp"
        new_revision: Path = RESOURCES_DIR / "diff" / "overload_v2.cpp"
        analyzer = CodeDiffAnalyzer(parser=CSourceCodeParser(), overload_analysis=True)
        changed_functions: List[FunctionDefinition] = [
            func
            for func, file in analyzer.get_changed_or_newly_overridden_functions(
                old_revision=old_revision, new_revision=new_revision
            )
        ]

        self.assertListEqual(
            [
                FunctionDefinition(
                    file=new_revision,
                    signature="foo*",
                    start_line=3,
                    end_line=5,
                    namespace=None,
                    class_name=None,
                ),
            ],
            changed_functions,
        )


if __name__ == "__main__":
    unittest.main()
