#include "Stdafx.h"

#include "BigInteger.h"

#include <iostream>
#include <locale>
#include <string>

BigInteger& BigInteger::operator++()
{
    ++_number;
    return *this;
}

BigInteger& BigInteger::operator--()
{
    --_number;
    return *this;
}

BigInteger& BigInteger::operator+=(BigInteger const& val)
{
    _number += val._number;
    return *this;
}

BigInteger& BigInteger::operator+=(int const& val)
{
    _number += val;
    return *this;
}

BigInteger& BigInteger::operator-=(BigInteger const& val)
{
    _number -= val._number;
    return *this;
}

BigInteger& BigInteger::operator-=(int const& val)
{
    _number -= val;
    return *this;
}

bool BigInteger::operator<(BigInteger const& val) const
{
    return _number < val._number;
}

bool BigInteger::operator==(BigInteger const& val) const
{
	std::cout << "Hello EqualsOp!" << std::endl;
    return _number == val._number;
}

bool BigInteger::operator==(int const& val) const
{
    return _number == val;
}

bool BigInteger::IsPositive() const
{
    return !_number.is_zero() && !IsNegative();
}

bool BigInteger::IsNegative() const
{
    return _number.sign() < 0;
}

bool BigInteger::IsZero() const
{
    return _number.is_zero();
}

int BigInteger::Compare(BigInteger const& other) const
{
    return *this < other ? -1 : *this == other ? 0 : 1;
}

BigInteger& BigInteger::operator*=(BigInteger const& val)
{
    _number *= val._number;
    return *this;
}

BigInteger& BigInteger::operator*=(int const& val)
{
    _number *= val;
    return *this;
}

BigInteger& BigInteger::operator/=(BigInteger const& val)
{
    _number /= val._number;
    return *this;
}

BigInteger& BigInteger::operator/=(int const& val)
{
    _number /= val;
    return *this;
}

std::ostream& operator<<(std::ostream& stream, BigInteger const& val)
{
    stream << val.toNarrowString();
    return stream;
}