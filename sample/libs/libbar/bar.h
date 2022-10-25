#pragma once
#include "ibar.h"

class Bar: public IBar
{
public:
    bool qux() override;
    bool norf() override;
};
