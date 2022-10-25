#include <iostream>
#include "testfoo.h"

FooSuite::FooSuite() {
    std::cout << "Creating FooSuite" << std::endl;
}

FooSuite::~FooSuite() = default;

void FooSuite::SetUp() {
    std::cout << "Setup FooSuite test case" << std::endl;
};

void FooSuite::TearDown() {
    std::cout << "Teardown FooSuite test case" << std::endl;
};

TEST_F(FooSuite, AlwaysTrue) {
    ASSERT_EQ(true, true);
}