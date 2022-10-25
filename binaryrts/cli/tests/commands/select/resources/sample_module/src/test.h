#pragma once

#include <gtest/gtest.h>

int Max(int a, int b) {
	return a > b ? a : b;
}

TEST(FooSuite, Max) {
	ASSERT_EQ(Max(1,2), 2);
}