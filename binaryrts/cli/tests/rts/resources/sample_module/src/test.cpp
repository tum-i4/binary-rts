#include "test.h"
#include "foo.h"

TEST_F(FooSuite, FooMax) {
    Foo foo;
    ASSERT_EQ(foo.Maximum(1,2), 2);
}

TEST_F(FooSuite, Max) {
    ASSERT_EQ(Max(1,2), 2);
}

TEST_F(FooSuite, MaxMacro) {
    ASSERT_EQ(MAX(1,2), 2);
}