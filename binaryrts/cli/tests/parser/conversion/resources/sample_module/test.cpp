#include "foo.h"

TEST_F(FooSuite, foo) {
    foo();
    foo();
}

TEST_F(FooSuite, bar) {
    foo();
}