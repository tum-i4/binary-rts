//
// Created by Daniel Elsner on 12.02.20.
//

#ifndef CPPCOVERAGE_TESTFOO_H
#define CPPCOVERAGE_TESTFOO_H


#include <gtest/gtest.h>
#include "mockbar.h"

// The fixture for testing class Foo.
class FooTest : public ::testing::Test {
public:
    static void SetUpTestSuite() {
        std::cout << "SetUpTestSuite FooTest" << std::endl;
    }

    static void TearDownTestSuite() {
        std::cout << "TearDownTestSuite FooTest" << std::endl;
    }
protected:

    // You can do set-up work for each test here.
    FooTest();

    // You can do clean-up work that doesn't throw exceptions here.
    virtual ~FooTest();

    // If the constructor and destructor are not enough for setting up
    // and cleaning up each test, you can define the following methods:

    // Code here will be called immediately after the constructor (right
    // before each test).
    virtual void SetUp();

    // Code here will be called immediately after each test (right
    // before the destructor).
    virtual void TearDown();

    // The mock bar
    MockBar m_bar;
};

class FooParameterizedTest :
    public testing::TestWithParam<int> {
public:
    static void SetUpTestSuite() {
        std::cout << "SetUpTestSuite FooParameterizedTest" << std::endl;
    }

    static void TearDownTestSuite() {
        std::cout << "TearDownTestSuite FooParameterizedTest" << std::endl;
    }
protected:
    virtual void SetUp() {
        std::cout << "Setup FooParameterizedTest test case" << std::endl;
    }
};

#endif //CPPCOVERAGE_TESTFOO_H
