import os
import unittest

from binaryrts.parser.conversion.lcov import LCOVCoverageConverter
from binaryrts.parser.coverage import (
    TestFunctionTraces,
    FunctionLookupTable,
    CoveredFunction,
    TEST_ID_SEP,
)


class LCOVCoverageConverterTestCase(unittest.TestCase):
    def test_convert(self):
        converter = LCOVCoverageConverter(
            test_traces=TestFunctionTraces(
                table={
                    f"{TEST_ID_SEP}FooSuite{TEST_ID_SEP}foo": {1, 3},
                    f"{TEST_ID_SEP}FooSuite{TEST_ID_SEP}Bar": {2, 3},
                }
            ),
            lookup=FunctionLookupTable(
                table={
                    f"test.cpp": [
                        CoveredFunction(
                            identifier=1,
                            file=f"test.cpp",
                            signature="TEST_F(FooSuite,foo)",
                            start=3,
                            end=6,
                        ),
                        CoveredFunction(
                            identifier=2,
                            file=f"test.cpp",
                            signature="TEST_F(FooSuite,bar)",
                            start=8,
                            end=10,
                        ),
                    ],
                    f"inc{os.sep}foo.h": [
                        CoveredFunction(
                            identifier=3,
                            file=f"inc{os.sep}foo.h",
                            signature="foo()",
                            start=3,
                            end=5,
                        ),
                        CoveredFunction(
                            identifier=4,
                            file=f"inc{os.sep}foo.h",
                            signature="bar()",
                            start=7,
                            end=9,
                        ),
                    ],
                }
            ),
            include_functions=True
        )
        result: str = converter.convert()
        self.assertEqual(
            result,
            f"""
SF:test.cpp
FN:3,TEST_F(FooSuitefoo)
FN:8,TEST_F(FooSuitebar)
FNDA:1,TEST_F(FooSuitefoo)
FNDA:1,TEST_F(FooSuitebar)
DA:3,1
DA:4,1
DA:5,1
DA:6,1
DA:8,1
DA:9,1
DA:10,1
end_of_record
SF:inc{os.sep}foo.h
FN:3,foo()
FN:7,bar()
FNDA:1,foo()
DA:3,1
DA:4,1
DA:5,1
DA:7,0
DA:8,0
DA:9,0
end_of_record
            """.strip(),
        )


if __name__ == "__main__":
    unittest.main()
