#include <gtest/gtest.h>
#include <iostream>
#include <fstream>

#ifdef TEST_LISTENER
#include "test_listener.h"

class CoverageEventListener : public testing::EmptyTestEventListener {
public:

    void OnTestProgramStart(const testing::UnitTest& test) override {
        startRun();
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
        BinaryRTSTestListener::TestSuiteEnd(testSuite.Passed() ? "PASSED" : "FAILED");
    }

    void OnTestProgramEnd(const testing::UnitTest& test) override {
        BinaryRTSTestListener::TestProgramEnd();
        finishRun();
    }

private:
    void finishRun() {
        std::cout << "After OnTestProgramEnd in CoverageEventListener" << std::endl;
    }
    void startRun() {
        std::cout << "Before OnTestProgramStart in CoverageEventListener" << std::endl;
    }
};

#endif

class CustomEnvironment : public ::testing::Environment {
public:
    ~CustomEnvironment() override = default;

    void SetUp() override {
        std::cout << "Global SetUp" << std::endl;
        std::ofstream file;
        file.open("output.txt");
        file << "Random text\n";
        file.close();
    }

    // Override this to define how to tear down the environment.
    void TearDown() override {
        std::cout << "Global TearDown" << std::endl;
    }
};

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    ::testing::AddGlobalTestEnvironment(new CustomEnvironment);
#ifdef TEST_SELECTION
    if (const char* excludes_file = GetTestExcludesFileFromEnv()) {
        std::string previousFilter = ::testing::GTEST_FLAG(filter);
        std::cout << "BEFORE: " << previousFilter << "\n";
        ::testing::GTEST_FLAG(filter) = ParseExcludesFileToGoogleTestFilter(excludes_file, previousFilter);
    }
#endif
#ifdef TEST_LISTENER
    // Gets hold of the event listener list.
    ::testing::UnitTest::GetInstance()->listeners().Append(new CoverageEventListener());
#endif
    return RUN_ALL_TESTS();
}