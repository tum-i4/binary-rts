#ifndef BINARY_RTS_TEST_LISTENER_H
#define BINARY_RTS_TEST_LISTENER_H

#include <string>

/*
 * Singleton that keeps track of executed tests and emits event messages to DynamoRIO.
 */
class BinaryRTSTestListener {
public:
    static const std::string TestCaseSeparator;

    static void TestProgramStart();

    static void TestSuiteStart(const std::string &testSuiteIdentifier);

    static void TestStart(const std::string &testIdentifier);

    static void TestEnd(const std::string &result);

    static void TestSuiteEnd(const std::string &result);

    static void TestProgramEnd();

    static BinaryRTSTestListener &GetInstance() {
        static BinaryRTSTestListener instance;
        return instance;
    }

private:
    BinaryRTSTestListener() = default;;
    static bool enableParameterizedTests;
    static bool isCurrentTestSuiteParameterized;
    static int testCounter;
    static int testSuiteCounter;
    static std::string currentTestSuiteIdentifier;
    static std::string currentTestIdentifier;
};

/*
 * Parses the provided excluded.txt file and
 * concatenates the contained excluded tests into a filter string interpreted by GoogleTest.
 */
std::string ParseExcludesFileToGoogleTestFilter(const std::string &path, const std::string &previousFilter);

/*
 * Searches for GoogleTest exclusion file in environment and returns file path (if any). 
 */
const char *GetTestExcludesFileFromEnv();

#endif //BINARY_RTS_TEST_LISTENER_H