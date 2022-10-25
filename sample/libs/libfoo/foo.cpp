#include "ibar.h"
#include "foo.h"
#include <iostream>
#include <cstdlib>
#include <ctime>

#define MAX(a,b) a > b ? a : b

const int g_magic = 42;

Foo::Foo(IBar& bar)
    :m_bar(bar) {};

bool Foo::baz(bool useQux) {
    srand(time(NULL));
    int random_number = std::rand();
    if (MAX(g_magic, random_number) > g_magic) {
        std::cout << "Random number " << random_number << " is larger than " << g_magic << std::endl;
    }
    if (useQux) {
        return m_bar.qux();
    } else {
        return m_bar.norf();
    }
}

int MacroMaxCalculator::Max(int a, int b) const {
    return MAX(a, b);
}

int SimpleMaxCalculator::Max(int a, int b) const {
    return a > b ? a : b;
}