"""
This script will recursively search for GoogleTest main files
and update them to include the BinaryRTS test listener.
"""
import argparse
import os
import re
from pathlib import Path

BINARY_RTS_LISTENER_HEADER: str = "test_listener.h"

MAIN_ROUTINE_FILTER: str = "main("
LISTENER_INCLUDE: str = """
// Start generated code by BinaryRTS.
#include "test_listener.h"

class CoverageEventListener : public testing::EmptyTestEventListener {
public:

    void OnTestProgramStart(const testing::UnitTest& test) override {
        BinaryRTSTestListener::TestProgramStart();
    }

    void OnTestSuiteStart(const testing::TestSuite& testSuite) override {
        BinaryRTSTestListener::TestSuiteStart(testSuite.name());
    }

    void OnTestStart(const testing::TestInfo& testInfo) override {
        BinaryRTSTestListener::TestStart(testInfo.name());
    }

    void OnTestEnd(const testing::TestInfo& test_info) override {
        BinaryRTSTestListener::TestEnd(test_info.result()->Passed() ? "PASSED": "FAILED");
    }

    void OnTestSuiteEnd(const testing::TestSuite& testSuite) override {
        BinaryRTSTestListener::TestSuiteEnd(testSuite.Passed() ? "PASSED": "FAILED");
    }

    void OnTestProgramEnd(const testing::UnitTest& test) override {
        BinaryRTSTestListener::TestProgramEnd();
    }
};
// End generated code.
"""
LISTENER_CODE: str = """
// Start generated code by BinaryRTS.
// Adds a listener to the end.
// googletest takes the ownership.
::testing::UnitTest::GetInstance()->listeners().Append(new CoverageEventListener());
// End generated code.
"""
SELECTOR_CODE: str = r"""
// Start generated code by BinaryRTS.
// Allows excluding tests from a file.
if (const char* excludes_file = GetTestExcludesFileFromEnv()) {
    std::string previousFilter = ::testing::GTEST_FLAG(filter);
    ::testing::GTEST_FLAG(filter) = ParseExcludesFileToGoogleTestFilter(excludes_file, previousFilter);
}
// End generated code.
"""


def parse_arguments() -> argparse.Namespace:
    """
    Define and parse program arguments.

    :return: arguments captured in object.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-path",
        "-i",
        default=os.path.abspath(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "..")
        ),
        help="Input path where to start searching for GoogleTest main files.",
    )
    parser.add_argument(
        "--regex",
        "-r",
        default="^.*test.*\\.c(|pp|c|xx)$",
        help="File regex to filter considered files.",
    )
    parser.add_argument(
        "--query",
        "-q",
        default="return RUN_ALL_TESTS()",
        help="Query string to look for in files.",
    )
    parser.add_argument("--selector", action="store_true")
    return parser.parse_args()


def main():
    # Parse arguments
    args = parse_arguments()

    # pre-compile regex
    file_pattern: re.Pattern = re.compile(args.regex, flags=re.IGNORECASE)

    print(f"Starting BinaryRTS GoogleTest Patcher with {args}...")

    # walk fs tree and check if file needs to be patched
    for root, dirs, files in os.walk(args.input_path):
        for file in files:
            file_path: Path = Path(os.path.join(root, file)).absolute()
            if re.match(file_pattern, file_path.__str__()):

                # lazy solution: we simply override all contents of the file
                file_content: str
                try:
                    file_content = file_path.read_text()
                except Exception as e:
                    print(f"Failed to read text from {file_path}: {e}")
                    continue

                if (
                    MAIN_ROUTINE_FILTER not in file_content
                    or args.query not in file_content
                ):
                    continue

                # we only patch if file isn't patched yet
                if LISTENER_INCLUDE in file_content:
                    print(f"Skipping already patched file {file_path}.")
                    continue

                print(f"Found GoogleTest main routine in {file_path}, will patch now.")

                out_file_content: str = ""
                for line in file_content.splitlines():
                    if MAIN_ROUTINE_FILTER in line:
                        line = f"{LISTENER_INCLUDE}\n{line}\n"
                    if args.query in line:
                        if args.selector:
                            # we insert the selector code right before the query
                            line = f"{SELECTOR_CODE}\n{line}"
                        else:
                            # we insert the listener code right before the query
                            line = f"{LISTENER_CODE}\n{line}"
                    out_file_content += f"{line}\n"

                try:
                    file_path.write_text(out_file_content)
                except Exception as e:
                    print(f"Failed to write text to {file_path}: {e}")
                    continue
                print(f"Done patching {file_path}.")


if __name__ == "__main__":
    main()
