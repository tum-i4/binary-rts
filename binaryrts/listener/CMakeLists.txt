project(BinaryRTSListener)

include(../../cmake/DynamoRIO.cmake)

set(binary_rts_listener_SRCS
    "test_listener.h"
    "test_listener.cpp"
)

# Append the default annotation source files to the sources.
use_DynamoRIO_annotations(binary_rts_listener, binary_rts_listener_SRCS)

# Declare the test listener library.
add_library(binary_rts_listener STATIC
    ${binary_rts_listener_SRCS}
)

# hacking in MSVC-specific flags
# set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} /MT")
# set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} /MTd")

# Include headers from DynamoRIO annotations.
include_directories("${DynamoRIO_ROOT}/include/annotations")

# Specify here the include directories exported by this library
# TODO: define with respect to `binaryrts` directory, to allow includes with <binaryrts/cov_listener.h>
target_include_directories(binary_rts_listener PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)