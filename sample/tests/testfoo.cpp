//
// Created by Daniel Elsner on 12.02.20.
//

#include <foo.h>
#include <iostream>
#include "testfoo.h"

using ::testing::Return;

FooTest::FooTest() {
    // Have qux return true by default
    EXPECT_CALL(m_bar, qux()).WillRepeatedly(Return(true));
    // Have norf return false by default
    EXPECT_CALL(m_bar, norf()).WillRepeatedly(Return(false));
}

// FooTest::~FooTest() {}; // same as below
FooTest::~FooTest() = default;

void FooTest::SetUp() {
    std::cout << "Setup FooTest test case" << std::endl;
};

void FooTest::TearDown() {
    std::cout << "Teardown FooTest test case" << std::endl;
};

// tests with fixtures
TEST_F(FooTest, ByDefaultBazTrueIsTrue) {
    Foo foo(m_bar);
    EXPECT_EQ(foo.baz(true), true);
}

TEST_F(FooTest, ByDefaultBazFalseIsFalse) {
    Foo foo(m_bar);
    EXPECT_EQ(foo.baz(false), false);
}

TEST_F(FooTest, SometimesBazFalseIsTrue) {
    Foo foo(m_bar);
    // Have norf return true for once
    EXPECT_CALL(m_bar, norf()).WillOnce(Return(true));
    EXPECT_EQ(foo.baz(false), true);
}

// simple test
TEST(FooTestSuite, AlwaysTrue) {
    ASSERT_EQ(true, true);
}

// simple test with long name
TEST(FoolTestCasesWithLongNames, testSomeVeryVeryVeryVe_ryVeryVeryVeryVeryVery_VeryVeryVeryVery_VeryVeryVeryVeryVeryVerylongNames) {
    ASSERT_EQ(true, true);
}

// value-parameterized test

TEST_P(FooParameterizedTest, LessThan5) {
    // Inside a test, access the test parameter with the GetParam() method
    // of the TestWithParam<T> class:
    EXPECT_LE(GetParam(), 5);
}

TEST_P(FooParameterizedTest, DividesBy2) {
    EXPECT_EQ(GetParam() % 2, 0);
}

INSTANTIATE_TEST_SUITE_P(FooParamInstantiationA,
    FooParameterizedTest,
    testing::Values(2, 4));

INSTANTIATE_TEST_SUITE_P(FooParamInstantiationB,
    FooParameterizedTest,
    testing::Values(0, 2));

TEST(FooParameterizedTest, normalTest) {
    EXPECT_TRUE(true);
}

// typed test

typedef testing::Types<MacroMaxCalculator, SimpleMaxCalculator> Implementations;

template <typename T>
class MaxCalculatorTest : public testing::Test {
public:
    static void SetUpTestSuite() {
        std::cout << "SetUpTestSuite MaxCalculatorTest<" << typeid(T).name() << ">" << std::endl;
    }

    static void TearDownTestSuite() {
        std::cout << "TearDownTestSuite FooParameterizedTest<" << typeid(T).name() << ">" << std::endl;
    }

    T value_;
protected:
    virtual void SetUp() {
        std::cout << "Setup MaxCalculatorTest test case" << std::endl;
    }
};

TYPED_TEST_SUITE(MaxCalculatorTest, Implementations);

TYPED_TEST(MaxCalculatorTest, ReturnsFirstForEqual) {
    EXPECT_EQ(1, this->value_.Max(1, 1));
}

TEST(MaxCalculatorTest, normalTest) {
    EXPECT_TRUE(true);
}

// type-parameterized test

TYPED_TEST_SUITE_P(MaxCalculatorTest);

TYPED_TEST_P(MaxCalculatorTest, ReturnsMaxCorrectly) {
    EXPECT_EQ(2, this->value_.Max(2, 1));
}

TYPED_TEST_P(MaxCalculatorTest, ReturnsMaxCorrectlyReverse) {
    EXPECT_EQ(2, this->value_.Max(1, 2));
}

TYPED_TEST_P(MaxCalculatorTest, ReturnsMaxCorrectlyNegative) {
    EXPECT_EQ(-1, this->value_.Max(-1, -2));
}

REGISTER_TYPED_TEST_SUITE_P(MaxCalculatorTest,
    ReturnsMaxCorrectly,
    ReturnsMaxCorrectlyReverse,
    ReturnsMaxCorrectlyNegative
    );

INSTANTIATE_TYPED_TEST_SUITE_P(CustomTypeParamTest, MaxCalculatorTest, Implementations);

using MyTypes = ::testing::Types<MacroMaxCalculator>;
INSTANTIATE_TYPED_TEST_SUITE_P(CustomTypeParamTest2, MaxCalculatorTest, MyTypes);