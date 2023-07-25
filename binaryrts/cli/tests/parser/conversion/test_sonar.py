import os
import unittest

from binaryrts.parser.conversion.sonar import SonarCoverageConverter
from binaryrts.parser.coverage import (
    TestFunctionTraces,
    FunctionLookupTable,
    CoveredFunction,
    TEST_ID_SEP,
)


class SonarCoverageConverterTestCase(unittest.TestCase):
    def test_convert(self):
        converter = SonarCoverageConverter(
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
        )
        result: str = converter.convert()
        self.assertEqual(
            result,
            f"""
<coverage version="1">
	<file path="test.cpp">
		<lineToCover lineNumber="3" covered="true"/>
		<lineToCover lineNumber="4" covered="true"/>
		<lineToCover lineNumber="5" covered="true"/>
		<lineToCover lineNumber="6" covered="true"/>
		<lineToCover lineNumber="8" covered="true"/>
		<lineToCover lineNumber="9" covered="true"/>
		<lineToCover lineNumber="10" covered="true"/>
	</file>
	<file path="inc{os.sep}foo.h">
		<lineToCover lineNumber="3" covered="true"/>
		<lineToCover lineNumber="4" covered="true"/>
		<lineToCover lineNumber="5" covered="true"/>
		<lineToCover lineNumber="7" covered="false"/>
		<lineToCover lineNumber="8" covered="false"/>
		<lineToCover lineNumber="9" covered="false"/>
	</file>
</coverage>
            """.strip(),
        )


if __name__ == "__main__":
    unittest.main()
