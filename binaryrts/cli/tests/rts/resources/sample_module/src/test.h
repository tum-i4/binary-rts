#pragma once

#include <gtest/gtest.h>
#include <iostream>

class FooSuite : public ::testing::Test {
public:
    static void SetUpTestSuite() {
        std::cout << "Setup FooSuite" << std::endl;
    }
};

#define MAX(a, b) a > b ? a : b