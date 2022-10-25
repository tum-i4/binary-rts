#include <iostream>

#define MAX(a, b) \
    a > b ? a : b

static const int factor = 4;

int weird_add(int a, int b)
{
    return a + b + factor + MAX(a, b);
}

namespace templates {

    template <class T>
    class CustomPair {
        T values[2];
    public:
        CustomPair(T first, T second)
        {
            values[0] = first; values[1] = second;
        }

        /* Member maximum function. */
        T GetMax()
        {
            return values[0] > values[1] ? values[0] : values[1];
        }
    };

    /* Template maximum function. */
    template <typename T>
    T GetMax(T a, T b) {
        return (a > b ? a : b);
    }

};

class A {
public:
    virtual int foo() {
        return 5;
    }
};


class __declspec(dllimport) C : public A {

public:
	int foo() override {
		return 30;
	}

	void bar(int c) {
	}

	int baz() {
        return MAX(1, 2);
    }
};

namespace Base
{
    template<typename X, typename Y>
    class __declspec(abc) Foo
        : public B
        , public C
    {
    	void foo() {}
    };

    template<typename Z, typename W>
    class Bar : private D<Z,W>
    {
    	void bar() {}
    };

    template<>
    void Foo<int,int>::foo() {printf("Hello world\n");}
}

int main()
{
    int a = 115, b = 36;
    templates::CustomPair<int> mypair(a, b);
    std::cout << "Max of pair (member): " << mypair.GetMax() << std::endl;
    std::cout << "Max of pair (global): " << templates::GetMax(a, b) << std::endl;
    C c;
    assert(c.foo() == 5);
    std::cout << "Successful assertion" << std::endl;
	return 0;
}