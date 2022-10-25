# Note: The contents of this file are inspired by (1) `drcov`, a coverage client for DynamoRIO,
# and (2) the DynamoRIO user documentation.
#
# (1) https://github.com/DynamoRIO/dynamorio/tree/release_9.0.1/clients/drcov/CMakeLists.txt
# (2) https://dynamorio.org/page_build_client.html

cmake_minimum_required(VERSION 3.14)

include(../../cmake/DynamoRIO.cmake)

# Create DynamoRIO client for BinaryRTS.
project(BinaryRTSClient)

# We do not need libc, and we avoid a 10x binary size increase.
# However, on Windows, `drfrontendlib` requires us to use libc.
if (UNIX)
    set(DynamoRIO_USE_LIBC OFF)
endif (UNIX)

# Add BinaryRTS client as shared library (DLL).
add_library(binary_rts_client SHARED client.c utils.c coverage.c modules.c)

# Configure custom DynamoRIO client.
configure_DynamoRIO_client(binary_rts_client)

# Add required DynamoRIO extensions.
use_DynamoRIO_extension(binary_rts_client drcontainers)
use_DynamoRIO_extension(binary_rts_client drmgr)
use_DynamoRIO_extension(binary_rts_client drx)
use_DynamoRIO_extension(binary_rts_client drreg)
use_DynamoRIO_extension(binary_rts_client drsyms)
use_DynamoRIO_extension(binary_rts_client drwrap)

# On Windows, we use drfrontendlib for easier filesystem ops.
# On Linux, such ops are more straightforward and therefore we don't require drfrontendlib.
if (WIN32)
    target_link_libraries(binary_rts_client drfrontendlib)
endif (WIN32)