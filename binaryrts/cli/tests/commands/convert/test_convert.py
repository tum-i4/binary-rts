import os.path
import unittest
from pathlib import Path
from typing import Optional

from typer.testing import CliRunner

from binaryrts.commands.convert import (
    app,
)
from binaryrts.parser.coverage import (
    FunctionLookupTable,
    TestFunctionTraces,
    TestFileTraces,
    COVERAGE_SEP,
    CoveredFunction,
    TEST_ID_SEP,
    GLOBAL_TEST_SETUP,
    FUNCTION_LOOKUP_FILE,
    TEST_FUNCTION_TRACES_FILE,
    TEST_LOOKUP_FILE,
    TEST_FILE_TRACES_FILE,
    PICKLE_FUNCTION_LOOKUP_FILE,
    PICKLE_TEST_FUNCTION_TRACES_FILE,
)

RESOURCES_DIR: Path = Path(os.path.dirname(__file__)) / "resources"
OUTPUT_DIR: Path = RESOURCES_DIR / "output"
SAMPLE_MODULE_DIR: Path = RESOURCES_DIR / "sample_module"
JAVA_MODULE_DIR: Path = RESOURCES_DIR / "java_module"


class CliConvertTestCase(unittest.TestCase):
    runner: Optional[CliRunner] = None

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._setup_sample_data()
        cls.runner = CliRunner()

    @classmethod
    def _setup_sample_data(cls):
        # create coverage files for single test suite `FooSuite` with
        # (1) global setup
        (SAMPLE_MODULE_DIR / "1.log").open(mode="w+").write(
            rf"""
ntdll.dll (C:\Windows\SYSTEM32\ntdll.dll)
KERNEL32.dll (C:\Windows\System32\KERNEL32.DLL)
sample_module.exe ({SAMPLE_MODULE_DIR / "build" / "sample_module.exe"})
    +0x0000000000051234{COVERAGE_SEP}{SAMPLE_MODULE_DIR / "src" / "main.cpp"}{COVERAGE_SEP}CustomEnvironment::SetUp{COVERAGE_SEP}8
"""
        )
        (SAMPLE_MODULE_DIR / "dump-lookup.log").open(mode="w+").write(
            f"""1;{GLOBAL_TEST_SETUP}\n"""
        )

        # (2) setup
        (SAMPLE_MODULE_DIR / "2.log").open(mode="w+").write(
            rf"""
ntdll.dll (C:\Windows\SYSTEM32\ntdll.dll)
KERNEL32.dll (C:\Windows\System32\KERNEL32.DLL)
sample_module.exe ({SAMPLE_MODULE_DIR / "build" / "sample_module.exe"})
	+0x000000000005e19d{COVERAGE_SEP}{SAMPLE_MODULE_DIR / "lib" / "gtest.cc"}{COVERAGE_SEP}testing::internal::PrettyUnitTestResultPrinter::OnTestStart{COVERAGE_SEP}3443
	+0x000000000005e200{COVERAGE_SEP}{SAMPLE_MODULE_DIR / "src" / "testfoo.h"}{COVERAGE_SEP}FooSuite::SetUpTestSuite{COVERAGE_SEP}9
"""
        )
        (SAMPLE_MODULE_DIR / "dump-lookup.log").open(mode="a+").write(
            """2;FooSuite___setup\n"""
        )
        # (3) test case `FooTestCase`
        (SAMPLE_MODULE_DIR / "3.log").open(mode="w+").write(
            rf"""
ntdll.dll (C:\Windows\SYSTEM32\ntdll.dll)
KERNEL32.dll (C:\Windows\System32\KERNEL32.DLL)
sample_module.exe ({SAMPLE_MODULE_DIR / "build" / "sample_module.exe"})
	+0x000000000005e13d{COVERAGE_SEP}{SAMPLE_MODULE_DIR / "lib" / "gtest.cc"}{COVERAGE_SEP}testing::internal::PrettyUnitTestResultPrinter::OnTestEnd{COVERAGE_SEP}4100
	+0x000000000005e221{COVERAGE_SEP}{SAMPLE_MODULE_DIR / "src" / "testfoo.cpp"}{COVERAGE_SEP}FooSuite::FooSuite{COVERAGE_SEP}5
	+0x000000000005e231{COVERAGE_SEP}{SAMPLE_MODULE_DIR / "src" / "testfoo.cpp"}{COVERAGE_SEP}FooSuite::FooSuite{COVERAGE_SEP}5
	+0x000000000005e241{COVERAGE_SEP}{SAMPLE_MODULE_DIR / "src" / "testfoo.cpp"}{COVERAGE_SEP}FooSuite::SetUp{COVERAGE_SEP}10
	+0x000000000005e251{COVERAGE_SEP}{SAMPLE_MODULE_DIR / "src" / "testfoo.cpp"}{COVERAGE_SEP}FooSuite::SetUp{COVERAGE_SEP}11
	+0x000000000005e261{COVERAGE_SEP}{SAMPLE_MODULE_DIR / "src" / "testfoo.cpp"}{COVERAGE_SEP}FooSuite::TearDown{COVERAGE_SEP}15
	+0x000000000005e281{COVERAGE_SEP}{SAMPLE_MODULE_DIR / "src" / "testfoo.cpp"}{COVERAGE_SEP}FooSuite::~FooSuite{COVERAGE_SEP}8
	+0x000000000005e291{COVERAGE_SEP}{SAMPLE_MODULE_DIR / "src" / "testfoo.cpp"}{COVERAGE_SEP}FooSuite_AlwaysTrue_Test::FooSuite_AlwaysTrue_Test{COVERAGE_SEP}18
	+0x000000000005e201{COVERAGE_SEP}{SAMPLE_MODULE_DIR / "src" / "testfoo.cpp"}{COVERAGE_SEP}FooSuite_AlwaysTrue_Test::TestBody{COVERAGE_SEP}18
	+0x000000000005e211{COVERAGE_SEP}{SAMPLE_MODULE_DIR / "src" / "testfoo.cpp"}{COVERAGE_SEP}FooSuite_AlwaysTrue_Test::~FooSuite_AlwaysTrue_Test{COVERAGE_SEP}18
            """
        )
        (SAMPLE_MODULE_DIR / "dump-lookup.log").open(mode="a+").write(
            """3;FooSuite.AlwaysTrue___PASSED\n"""
        )
        # (4) teardown
        (SAMPLE_MODULE_DIR / "4.log").open(mode="w+").write(
            rf"""
ntdll.dll (C:\Windows\SYSTEM32\ntdll.dll)
KERNEL32.dll (C:\Windows\System32\KERNEL32.DLL)
sample_module.exe ({SAMPLE_MODULE_DIR / "build" / "sample_module.exe"})
	+0x000000000005e13d{COVERAGE_SEP}{SAMPLE_MODULE_DIR / "lib" / "gtest.cc"}{COVERAGE_SEP}testing::internal::PrettyUnitTestResultPrinter::OnTestEnd{COVERAGE_SEP}4100
	+0x000000000005e221{COVERAGE_SEP}{SAMPLE_MODULE_DIR / "src" / "testfoo.h"}{COVERAGE_SEP}FooSuite::TearDownTestSuite{COVERAGE_SEP}13
            """
        )
        (SAMPLE_MODULE_DIR / "dump-lookup.log").open(mode="a+").write(
            """4;FooSuite___PASSED\n"""
        )
        # (4) global teardown
        (SAMPLE_MODULE_DIR / "5.log").open(mode="w+").write(
            rf"""
ntdll.dll (C:\Windows\SYSTEM32\ntdll.dll)
KERNEL32.dll (C:\Windows\System32\KERNEL32.DLL)
sample_module.exe ({SAMPLE_MODULE_DIR / "build" / "sample_module.exe"})
    +0x0000000000051238{COVERAGE_SEP}{SAMPLE_MODULE_DIR / "src" / "main.cpp"}{COVERAGE_SEP}CustomEnvironment::TearDown{COVERAGE_SEP}13
"""
        )
        (SAMPLE_MODULE_DIR / "dump-lookup.log").open(mode="a+").write(
            f"""5;{GLOBAL_TEST_SETUP}\n"""
        )
        # (6) global setup syscalls
        (SAMPLE_MODULE_DIR / "1.syscalls.log").open(mode="w+").write("")
        # (6) setup syscalls
        (SAMPLE_MODULE_DIR / "2.syscalls.log").open(mode="w+").write(
            rf"""
{SAMPLE_MODULE_DIR / "src" / "setup.txt"}
            """
        )
        # (7) execution syscalls
        (SAMPLE_MODULE_DIR / "3.syscalls.log").open(mode="w+").write(
            rf"""
{SAMPLE_MODULE_DIR / "src" / "test.txt"}
            """
        )

        # create coverage files for 2 Java test suites
        # (1) test suite 1
        (JAVA_MODULE_DIR / "1234_123456789.log").open(mode="w+").write(
            rf"""
sample_lib.dll ({JAVA_MODULE_DIR / "sample_lib.dll"})
	+0x00001{COVERAGE_SEP}{JAVA_MODULE_DIR / "foo.cpp"}{COVERAGE_SEP}foo{COVERAGE_SEP}2
    """
        )
        (JAVA_MODULE_DIR / "dump-lookup.log").open(mode="w+").write(
            """1234_123456789;edu.tum.sse.binaryrts.FooTest\n"""
        )
        # (2) test suite 2
        (JAVA_MODULE_DIR / "1235_123456789.log").open(mode="w+").write(
            rf"""
other_lib.dll ({JAVA_MODULE_DIR / "other_lib.dll"})
	+0x00004{COVERAGE_SEP}{JAVA_MODULE_DIR / "foo.cpp"}{COVERAGE_SEP}bar{COVERAGE_SEP}6
    """
        )
        (JAVA_MODULE_DIR / "dump-lookup.log").open(mode="a+").write(
            """1235_123456789;edu.tum.sse.binaryrts.BarTest\n"""
        )

    def test_convert_cpp(self):
        result = self.runner.invoke(
            app,
            [
                "-i",
                SAMPLE_MODULE_DIR.__str__(),
                "-o",
                OUTPUT_DIR.__str__(),
                "--regex",
                r".*sample\_module[\/|\\]src.*",
                "--repo",
                SAMPLE_MODULE_DIR.__str__(),
                "--processes",
                1,
                "cpp",
                "--ext",
                ".log",
                "--test-lookup",
            ],
            catch_exceptions=True,
        )
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(OUTPUT_DIR.exists())
        self.assertTrue((OUTPUT_DIR / FUNCTION_LOOKUP_FILE).exists())
        self.assertTrue((OUTPUT_DIR / TEST_FUNCTION_TRACES_FILE).exists())
        # check if content of csv files is correct
        lookup_table: FunctionLookupTable = FunctionLookupTable.from_csv(
            OUTPUT_DIR / FUNCTION_LOOKUP_FILE
        )
        self.assertEqual(
            FunctionLookupTable(
                table={
                    f"src{os.sep}main.cpp": [
                        CoveredFunction(
                            0,
                            f"src{os.sep}main.cpp",
                            "SetUp()",
                            7,
                            9,
                            "override,virtual",
                            None,
                            "CustomEnvironment",
                        ),
                        CoveredFunction(
                            1,
                            f"src{os.sep}main.cpp",
                            "TearDown()",
                            12,
                            14,
                            "override,virtual",
                            None,
                            "CustomEnvironment",
                        ),
                        CoveredFunction(
                            2,
                            f"src{os.sep}main.cpp",
                            "main(int,char**)",
                            17,
                            21,
                            None,
                            None,
                            None,
                        ),
                        CoveredFunction(
                            3,
                            f"src{os.sep}main.cpp",
                            "~CustomEnvironment()",
                            5,
                            5,
                            "override,virtual",
                            None,
                            "CustomEnvironment",
                        ),
                    ],
                    f"src{os.sep}testfoo.h": [
                        CoveredFunction(
                            4,
                            f"src{os.sep}testfoo.h",
                            "SetUpTestSuite()",
                            8,
                            10,
                            "static",
                            None,
                            "FooSuite",
                        ),
                        CoveredFunction(
                            5,
                            f"src{os.sep}testfoo.h",
                            "TearDownTestSuite()",
                            12,
                            14,
                            "static",
                            None,
                            "FooSuite",
                        ),
                    ],
                    f"src{os.sep}testfoo.cpp": [
                        CoveredFunction(
                            6,
                            f"src{os.sep}testfoo.cpp",
                            "FooSuite()",
                            4,
                            6,
                            None,
                            None,
                            "FooSuite",
                        ),
                        CoveredFunction(
                            7,
                            f"src{os.sep}testfoo.cpp",
                            "SetUp()",
                            10,
                            12,
                            None,
                            None,
                            "FooSuite",
                        ),
                        CoveredFunction(
                            8,
                            f"src{os.sep}testfoo.cpp",
                            "TEST_F(FooSuite,AlwaysTrue)",
                            18,
                            20,
                            None,
                            None,
                            None,
                        ),
                        CoveredFunction(
                            9,
                            f"src{os.sep}testfoo.cpp",
                            "TearDown()",
                            14,
                            16,
                            None,
                            None,
                            "FooSuite",
                        ),
                    ],
                }
            ),
            lookup_table,
        )
        test_function_traces: TestFunctionTraces = TestFunctionTraces.from_csv(
            OUTPUT_DIR / TEST_FUNCTION_TRACES_FILE
        )
        self.assertEqual(
            TestFunctionTraces(
                table={
                    f"sample_module{TEST_ID_SEP}{GLOBAL_TEST_SETUP}{TEST_ID_SEP}*": {
                        0,
                        1,
                    },
                    f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}*": {
                        4,
                        5,
                    },
                    f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}AlwaysTrue": {
                        6,
                        7,
                        8,
                        9,
                    },
                }
            ),
            test_function_traces,
        )

    def test_convert_cpp_with_test_lookup(self):
        result = self.runner.invoke(
            app,
            [
                "-i",
                SAMPLE_MODULE_DIR.__str__(),
                "-o",
                OUTPUT_DIR.__str__(),
                "--regex",
                r".*sample\_module[\/|\\]src.*",
                "--repo",
                SAMPLE_MODULE_DIR.__str__(),
                "--processes",
                1,
                "cpp",
                "--ext",
                ".log",
            ],
            catch_exceptions=True,
        )
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(OUTPUT_DIR.exists())
        self.assertTrue((OUTPUT_DIR / FUNCTION_LOOKUP_FILE).exists())
        self.assertTrue((OUTPUT_DIR / TEST_LOOKUP_FILE).exists())
        self.assertTrue((OUTPUT_DIR / TEST_FUNCTION_TRACES_FILE).exists())
        # check if content of csv files is correct
        lookup_table: FunctionLookupTable = FunctionLookupTable.from_csv(
            OUTPUT_DIR / FUNCTION_LOOKUP_FILE
        )
        self.assertEqual(
            FunctionLookupTable(
                table={
                    f"src{os.sep}main.cpp": [
                        CoveredFunction(
                            0,
                            f"src{os.sep}main.cpp",
                            "SetUp()",
                            7,
                            9,
                            "override,virtual",
                            None,
                            "CustomEnvironment",
                        ),
                        CoveredFunction(
                            1,
                            f"src{os.sep}main.cpp",
                            "TearDown()",
                            12,
                            14,
                            "override,virtual",
                            None,
                            "CustomEnvironment",
                        ),
                        CoveredFunction(
                            2,
                            f"src{os.sep}main.cpp",
                            "main(int,char**)",
                            17,
                            21,
                            None,
                            None,
                            None,
                        ),
                        CoveredFunction(
                            3,
                            f"src{os.sep}main.cpp",
                            "~CustomEnvironment()",
                            5,
                            5,
                            "override,virtual",
                            None,
                            "CustomEnvironment",
                        ),
                    ],
                    f"src{os.sep}testfoo.h": [
                        CoveredFunction(
                            4,
                            f"src{os.sep}testfoo.h",
                            "SetUpTestSuite()",
                            8,
                            10,
                            "static",
                            None,
                            "FooSuite",
                        ),
                        CoveredFunction(
                            5,
                            f"src{os.sep}testfoo.h",
                            "TearDownTestSuite()",
                            12,
                            14,
                            "static",
                            None,
                            "FooSuite",
                        ),
                    ],
                    f"src{os.sep}testfoo.cpp": [
                        CoveredFunction(
                            6,
                            f"src{os.sep}testfoo.cpp",
                            "FooSuite()",
                            4,
                            6,
                            None,
                            None,
                            "FooSuite",
                        ),
                        CoveredFunction(
                            7,
                            f"src{os.sep}testfoo.cpp",
                            "SetUp()",
                            10,
                            12,
                            None,
                            None,
                            "FooSuite",
                        ),
                        CoveredFunction(
                            8,
                            f"src{os.sep}testfoo.cpp",
                            "TEST_F(FooSuite,AlwaysTrue)",
                            18,
                            20,
                            None,
                            None,
                            None,
                        ),
                        CoveredFunction(
                            9,
                            f"src{os.sep}testfoo.cpp",
                            "TearDown()",
                            14,
                            16,
                            None,
                            None,
                            "FooSuite",
                        ),
                    ],
                }
            ),
            lookup_table,
        )
        test_function_traces: TestFunctionTraces = TestFunctionTraces.from_csv(
            OUTPUT_DIR / TEST_FUNCTION_TRACES_FILE, OUTPUT_DIR / TEST_LOOKUP_FILE
        )
        self.assertEqual(
            TestFunctionTraces(
                table={
                    f"sample_module{TEST_ID_SEP}{GLOBAL_TEST_SETUP}{TEST_ID_SEP}*": {
                        0,
                        1,
                    },
                    f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}*": {
                        4,
                        5,
                    },
                    f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}AlwaysTrue": {
                        6,
                        7,
                        8,
                        9,
                    },
                }
            ),
            test_function_traces,
        )

    def test_convert_cpp_with_pickle_serialization(self):
        result = self.runner.invoke(
            app,
            [
                "-i",
                SAMPLE_MODULE_DIR.__str__(),
                "-o",
                OUTPUT_DIR.__str__(),
                "--regex",
                r".*sample\_module[\/|\\]src.*",
                "--repo",
                SAMPLE_MODULE_DIR.__str__(),
                "--processes",
                1,
                "--binary",
                "cpp",
                "--ext",
                ".log",
            ],
            catch_exceptions=True,
        )
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(OUTPUT_DIR.exists())
        self.assertTrue((OUTPUT_DIR / PICKLE_FUNCTION_LOOKUP_FILE).exists())
        self.assertTrue((OUTPUT_DIR / PICKLE_TEST_FUNCTION_TRACES_FILE).exists())
        # check if content of csv files is correct
        lookup_table: FunctionLookupTable = FunctionLookupTable.from_pickle(
            OUTPUT_DIR / PICKLE_FUNCTION_LOOKUP_FILE
        )
        expected_lookup_table: FunctionLookupTable = FunctionLookupTable(
            table={
                f"src{os.sep}main.cpp": [
                    CoveredFunction(
                        0,
                        f"src{os.sep}main.cpp",
                        "SetUp()",
                        7,
                        9,
                        "override,virtual",
                        None,
                        "CustomEnvironment",
                    ),
                    CoveredFunction(
                        1,
                        f"src{os.sep}main.cpp",
                        "TearDown()",
                        12,
                        14,
                        "override,virtual",
                        None,
                        "CustomEnvironment",
                    ),
                    CoveredFunction(
                        2,
                        f"src{os.sep}main.cpp",
                        "main(int,char**)",
                        17,
                        21,
                        None,
                        None,
                        None,
                    ),
                    CoveredFunction(
                        3,
                        f"src{os.sep}main.cpp",
                        "~CustomEnvironment()",
                        5,
                        5,
                        "override,virtual",
                        None,
                        "CustomEnvironment",
                    ),
                ],
                f"src{os.sep}testfoo.h": [
                    CoveredFunction(
                        4,
                        f"src{os.sep}testfoo.h",
                        "SetUpTestSuite()",
                        8,
                        10,
                        "static",
                        None,
                        "FooSuite",
                    ),
                    CoveredFunction(
                        5,
                        f"src{os.sep}testfoo.h",
                        "TearDownTestSuite()",
                        12,
                        14,
                        "static",
                        None,
                        "FooSuite",
                    ),
                ],
                f"src{os.sep}testfoo.cpp": [
                    CoveredFunction(
                        6,
                        f"src{os.sep}testfoo.cpp",
                        "FooSuite()",
                        4,
                        6,
                        None,
                        None,
                        "FooSuite",
                    ),
                    CoveredFunction(
                        7,
                        f"src{os.sep}testfoo.cpp",
                        "SetUp()",
                        10,
                        12,
                        None,
                        None,
                        "FooSuite",
                    ),
                    CoveredFunction(
                        8,
                        f"src{os.sep}testfoo.cpp",
                        "TEST_F(FooSuite,AlwaysTrue)",
                        18,
                        20,
                        None,
                        None,
                        None,
                    ),
                    CoveredFunction(
                        9,
                        f"src{os.sep}testfoo.cpp",
                        "TearDown()",
                        14,
                        16,
                        None,
                        None,
                        "FooSuite",
                    ),
                ],
            }
        )
        self.assertEqual(
            expected_lookup_table,
            lookup_table,
        )
        test_function_traces: TestFunctionTraces = TestFunctionTraces.from_pickle(
            OUTPUT_DIR / PICKLE_TEST_FUNCTION_TRACES_FILE,
        )
        self.assertEqual(
            TestFunctionTraces(
                table={
                    f"sample_module{TEST_ID_SEP}{GLOBAL_TEST_SETUP}{TEST_ID_SEP}*": {
                        0,
                        1,
                    },
                    f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}*": {
                        4,
                        5,
                    },
                    f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}AlwaysTrue": {
                        6,
                        7,
                        8,
                        9,
                    },
                }
            ),
            test_function_traces,
        )

    def test_convert_cpp_java_dir(self):
        result = self.runner.invoke(
            app,
            [
                "-i",
                JAVA_MODULE_DIR.__str__(),
                "-o",
                OUTPUT_DIR.__str__(),
                "--processes",
                1,
                "--repo",
                JAVA_MODULE_DIR.__str__(),
                "cpp",
                "--ext",
                ".log",
                "--java",
                "--test-lookup",
            ],
            catch_exceptions=True,
        )
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(OUTPUT_DIR.exists())
        self.assertTrue((OUTPUT_DIR / FUNCTION_LOOKUP_FILE).exists())
        self.assertTrue((OUTPUT_DIR / TEST_FUNCTION_TRACES_FILE).exists())
        # check if content of csv files is correct
        lookup_table: FunctionLookupTable = FunctionLookupTable.from_csv(
            OUTPUT_DIR / FUNCTION_LOOKUP_FILE
        )
        self.assertEqual(
            FunctionLookupTable(
                table={
                    f"foo.cpp": [
                        CoveredFunction(
                            0,
                            f"foo.cpp",
                            "bar()",
                            5,
                            7,
                            None,
                            None,
                            None,
                        ),
                        CoveredFunction(
                            1,
                            f"foo.cpp",
                            "foo()",
                            1,
                            3,
                            None,
                            None,
                            None,
                        ),
                    ],
                }
            ),
            lookup_table,
        )
        test_function_traces: TestFunctionTraces = TestFunctionTraces.from_csv(
            OUTPUT_DIR / TEST_FUNCTION_TRACES_FILE
        )
        self.assertEqual(
            TestFunctionTraces(
                table={
                    f"*{TEST_ID_SEP}edu.tum.sse.binaryrts.FooTest{TEST_ID_SEP}*": {1},
                    f"*{TEST_ID_SEP}edu.tum.sse.binaryrts.BarTest{TEST_ID_SEP}*": {0},
                }
            ),
            test_function_traces,
        )

    def test_convert_syscalls(self):
        result = self.runner.invoke(
            app,
            [
                "-i",
                SAMPLE_MODULE_DIR.__str__(),
                "-o",
                OUTPUT_DIR.__str__(),
                "--regex",
                r".*sample\_module[\/|\\]src.*",
                "--repo",
                SAMPLE_MODULE_DIR.__str__(),
                "syscalls",
                "--ext",
                ".syscalls.log",
            ],
            catch_exceptions=True,
        )
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(OUTPUT_DIR.exists())
        self.assertTrue((OUTPUT_DIR / TEST_FILE_TRACES_FILE).exists())
        # check if content of csv files is correct
        test_file_traces: TestFileTraces = TestFileTraces.from_csv(
            OUTPUT_DIR / TEST_FILE_TRACES_FILE
        )
        self.assertEqual(
            TestFileTraces(
                table={
                    f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}AlwaysTrue": {
                        "test.txt"
                    },
                    f"sample_module{TEST_ID_SEP}FooSuite{TEST_ID_SEP}*": {"setup.txt"},
                }
            ),
            test_file_traces,
        )


if __name__ == "__main__":
    unittest.main()
