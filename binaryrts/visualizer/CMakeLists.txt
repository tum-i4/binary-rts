cmake_minimum_required(VERSION 3.14)

include(../../cmake/DynamoRIO.cmake)

set(CMAKE_CXX_STANDARD 17)

project(BinaryRTSCoverageVisualizerTool)

set(visualizer_SRCS "main.cpp" "visualizer.cpp" "visualizer.h")

add_executable(binary_rts_visualizer ${visualizer_SRCS})

if (UNIX)
    set_target_properties(binary_rts_visualizer
            PROPERTIES
            RUNTIME_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}"
            )
    set(DynamoRIO_USE_LIBC OFF)
endif (UNIX)
configure_DynamoRIO_standalone(binary_rts_visualizer)

if (WIN32)
    # Fix problems with drsyms_static: https://github.com/DynamoRIO/dynamorio/issues/3363
    set_target_properties(drsyms_static PROPERTIES
            INTERFACE_LINK_LIBRARIES "libcpmt;libcmt;dynamorio;dbghelp;${DynamoRIO_ROOT}/lib${_DR_bits}/dbghelp_imports.lib;drcontainers;dwarf;elftc"
            )
endif (WIN32)
use_DynamoRIO_extension(binary_rts_visualizer drsyms_static)

if (WIN32)
    # Fix for Windows where in some scenarios a Debug/ or Release/ directory is created by cmake
    # which separates the EXE from the DLLs.
    set_target_properties(binary_rts_visualizer
            PROPERTIES
            RUNTIME_OUTPUT_DIRECTORY_DEBUG ${CMAKE_CURRENT_BINARY_DIR})
endif(WIN32)
# Find and copy dynamorio.dll and dbghelp.dll
DynamoRIO_get_full_path(DR_TARGET_LOCATION dynamorio "${location_suffix}")
file(COPY "${DR_TARGET_LOCATION}" DESTINATION ${PROJECT_BINARY_DIR})
if (WIN32)
    file(COPY "${DynamoRIO_ROOT}/ext/lib${_DR_bits}/${_DR_type}/dbghelp.dll" DESTINATION ${PROJECT_BINARY_DIR})
endif (WIN32)