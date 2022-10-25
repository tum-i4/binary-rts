#include <cstdio>

namespace bar {
    namespace {
        template<typename T>
        struct X {
            struct Y {};
        };
     }

    template<>
    struct X<int> {
       void foo() {
           printf("foo\n");
       }
    };

    namespace baz {
        struct Z {
            static void bar() {
                printf("bar\n");
            }
        };
    }

    void foo() {
        auto x = X<int>{};
        x.foo();
    }
}

namespace foo {
    template<typename T>
    struct A
    {
        // template member (defined inside struct)
        void f(T) { printf("temp\n"); }
        // declared in struct, defined outside struct
        void g(T);

        struct B {};      // member class

        template<class U> // member class template
        struct C {};
    };

    template<typename T>
    void A<T>::g(T) { printf("temp out\n"); }

    template<> // specialization
    struct A<int>
    {
        void f(int); // member function of a specialization
    };
    // template<> not used for a member of a specialization
    void A<int>::f(int) { /* ... */ printf("yay\n"); }

    template<> // specialization of a member class
    struct A<char>::B
    {
        void f();
    };
    // template<> not used for a member of a specialized member class either
    void A<char>::B::f() { /* ... */ printf("nay\n"); }

    template<> // specialization of a member class template
    template<class U>
    struct A<char>::C
    {
        void f();
        void g() {

        }
    };
    // template<> is used when defining a member of an explicitly
    // specialized member class template specialized as a class template
    template<>
    template<class U>
    void A<char>::C<U>::f() { /* ... */ printf("bay\n"); }
}

int main () {
    auto i = foo::A<int>{};
    i.f(1);

    auto l = foo::A<long>{};
    l.f(2L);
    l.g(1L);

    auto c = foo::A<char>::C<int>{};
    c.f();

    bar::foo();

    bar::baz::Z::bar();
    return 0;
}