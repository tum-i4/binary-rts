//
// Created by Daniel Elsner on 12.02.20.
//

#ifndef CPPCOVERAGE_MOCKBAR_H
#define CPPCOVERAGE_MOCKBAR_H

#include "gmock/gmock.h"
#include "ibar.h"

class MockBar : public IBar {
public:
    MOCK_METHOD0(qux, bool());
    MOCK_METHOD0(norf, bool());
};

#endif //CPPCOVERAGE_MOCKBAR_H
