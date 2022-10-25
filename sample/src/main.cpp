#include "bar.h"
#include "foo.h"
#include "iostream"

int main(int argc, char *argv[]) {
    std::cout << "Starting up...\n" << std::endl;
    Bar bar;
    Foo foo(bar);
    foo.baz(true);
    foo.baz(false);
    std::cout << "Done.\n" << std::endl;
    return 0;
}
