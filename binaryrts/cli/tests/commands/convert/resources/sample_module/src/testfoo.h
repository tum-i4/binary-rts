#ifndef CPPCOVERAGE_TESTFOO_H
#define CPPCOVERAGE_TESTFOO_H

#include <gtest/gtest.h>

class FooSuite : public ::testing::Test {
public:
    static void SetUpTestSuite() {
        std::cout << "Setup FooTest" << std::endl;
    }

    static void TearDownTestSuite() {
        std::cout << "Teardown FooTest" << std::endl;
    }
protected:
    FooSuite();
    virtual ~FooSuite();
    virtual void SetUp();
    virtual void TearDown();
};


#endif //CPPCOVERAGE_TESTFOO_H
