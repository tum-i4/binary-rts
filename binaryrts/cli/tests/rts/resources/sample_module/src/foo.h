class Foo {
public:
	virtual int Maximum(int a, int b) {
		return a > b ? a : b;
	}
};

int Max(int c, int d) {
	return c > d ? c : d;
}