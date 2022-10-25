#include <stdio.h>

void foo(int x) {
	printf("int:%d\n", x);
}

void foo(short x) {
	printf("short:%d\n", x);
}

int main() {
	short i = 10;
	foo(i);
	return 0;
}