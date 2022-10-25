#pragma once

class IBar;

class Foo
{
public:
    explicit Foo(IBar& bar);
    bool baz(bool useQux);
protected:
    IBar& m_bar;
};

class MaxCalculator {
public:
    virtual ~MaxCalculator() {}

    virtual int Max(int a, int b) const = 0;
};

class MacroMaxCalculator : public MaxCalculator {
public:
    int Max(int a, int b) const override;
};

class SimpleMaxCalculator : public MaxCalculator {
public:
    int Max(int a, int b) const override;
};