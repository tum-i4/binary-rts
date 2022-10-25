#include <gtest/gtest.h>

class CustomEnvironment : public ::testing::Environment {
public:
    ~CustomEnvironment() override {}

    void SetUp() override {
        std::cout << "Global SetUp" << std::endl;
    }

    // Override this to define how to tear down the environment.
    void TearDown() override {
        std::cout << "Global TearDown" << std::endl;
    }
};

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    ::testing::AddGlobalTestEnvironment(new CustomEnvironment);
    return RUN_ALL_TESTS();
}