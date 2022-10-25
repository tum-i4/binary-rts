#include <string>
#include <algorithm>
#include <fstream>
#include <iostream>
#include <cstdlib>
#include <vector>
#include <sstream>

#include "test_listener.h"
#include "dr_annotations.h"

#ifdef __linux__
    #include <unistd.h>  // readlink()
#elif _WIN32
    #include <windows.h> // GetModuleFileName()
#endif

#define DEBUG 0
#define DR_LOG(format, ...) \
    DYNAMORIO_ANNOTATE_LOG(format, ##__VA_ARGS__)

namespace {
    const char *globalTestSetupDumpIdentifier = "GLOBAL_TEST_SETUP";
    const std::string testIdSeparator = "!!!";
    constexpr size_t maxPathLength = 512;

    std::vector<std::string> split(const std::string &s, char delim) {
        std::vector<std::string> result;
        std::stringstream ss(s);
        std::string item;

        while (getline(ss, item, delim)) {
            result.push_back(item);
        }

        return result;
    }

    std::string getCurrentExecutableName() {
        std::string executableName;
#ifdef __linux__
        char exe[maxPathLength] = {0};
        ssize_t ret;
        ret = readlink("/proc/self/exe", exe, sizeof(exe) - 1);
        if (ret != -1) {
            executableName = split(exe, '/').back();
        }
#elif _WIN32
        TCHAR exe[maxPathLength] = {0};
        DWORD bufSize = sizeof(exe) / sizeof(*exe);
        if (GetModuleFileName(NULL, exe, bufSize) < bufSize) {
            executableName = split(exe, '\\').back();
        }
#endif
        return executableName;
    }
}

const std::string BinaryRTSTestListener::TestCaseSeparator = ".";
bool BinaryRTSTestListener::enableParameterizedTests = true;  // By default, we consider each value- or type-parameterized test case.
bool BinaryRTSTestListener::isCurrentTestSuiteParameterized = false;
int BinaryRTSTestListener::testCounter = 0;
int BinaryRTSTestListener::testSuiteCounter = 0;
std::string BinaryRTSTestListener::currentTestIdentifier;
std::string BinaryRTSTestListener::currentTestSuiteIdentifier;

void DumpCoverage(const char *dumpId) {
#if DEBUG
    std::cout << "Dumping with ID: " << dumpId << std::endl;
#endif
    DR_LOG(dumpId);
    }

void BinaryRTSTestListener::TestProgramStart() {
    DumpCoverage("BEFORE_PROGRAM_START");
}

void BinaryRTSTestListener::TestSuiteStart(const std::string &testSuiteIdentifier) {
    currentTestSuiteIdentifier = std::string(testSuiteIdentifier);
    if (currentTestSuiteIdentifier.find('/') != std::string::npos) {
        isCurrentTestSuiteParameterized = true;
    }
    if (testSuiteCounter++ == 0) {
        DumpCoverage(globalTestSetupDumpIdentifier);
    }
}

void BinaryRTSTestListener::TestStart(const std::string &testIdentifier) {
    currentTestIdentifier = std::string(currentTestSuiteIdentifier + TestCaseSeparator + testIdentifier);
    if (testCounter++ == 0) {
        std::string message = std::string(currentTestSuiteIdentifier + "___setup");
        DumpCoverage(message.c_str());
    }
}

void BinaryRTSTestListener::TestEnd(const std::string &result) {
    // Trigger coverage dump after each test case for test-specific coverage.
    // We encode the test result in the dump identifier.
    if (enableParameterizedTests || !isCurrentTestSuiteParameterized) {
        std::string message = std::string(currentTestIdentifier + "___" + result);
        DumpCoverage(message.c_str());
    }
}

void BinaryRTSTestListener::TestSuiteEnd(const std::string &result) {
    std::string message = std::string(currentTestSuiteIdentifier + "___" + result);
    DumpCoverage(message.c_str());
    testCounter = 0;
    isCurrentTestSuiteParameterized = false;
}

void BinaryRTSTestListener::TestProgramEnd() {
    testSuiteCounter = 0;
    DumpCoverage(globalTestSetupDumpIdentifier);
}

std::string
ParseExcludesFileToGoogleTestFilter(const std::string &path, const std::string &previousFilter = std::string()) {
    std::ifstream file(path);
    std::cout << "Starting to parse excluded tests from " << path << "\n";
    std::string testFilter = "-";

    std::string executableName = getCurrentExecutableName();

    // In case previous filter is non-empty, we need to either
    // (1) append to the end with ':' (if '-' already present) or
    // (2) append with '-' to the end.
    if (!previousFilter.empty()) {
        std::size_t excludesFilterPos = previousFilter.find('-');
        if (excludesFilterPos == std::string::npos) {
            testFilter = previousFilter + "-";
        } else {
            testFilter = previousFilter + ":";
        }
    }

    if (file.is_open()) {
        std::string line;
        uint64_t counter = 0;
        while (std::getline(file, line)) {
            // Remove test module name (i.e., test executable name) prefix from identifier.
            std::size_t moduleIdEnd = line.find(testIdSeparator);
            // TODO: We could filter here based on the executable name.
//            if (!executableName.empty()) {
//                std::string moduleName = line.substr(0, moduleIdEnd);
//                if (moduleName != executableName)
//                    continue;
//            }
            line = line.substr(moduleIdEnd + testIdSeparator.size());
            line.replace(line.find(testIdSeparator), testIdSeparator.size(), ".");
            if (counter > 0) {
                testFilter += ":";
            }
            testFilter += line;
            ++counter;
        }
        std::cout << "Found " << counter << " tests: " << testFilter << "\n";
        file.close();
    }

    return testFilter;
}

const char *GetTestExcludesFileFromEnv() {
    return std::getenv("GTEST_EXCLUDES_FILE");
}
