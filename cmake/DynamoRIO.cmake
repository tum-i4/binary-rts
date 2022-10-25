# Fetch the DynamoRIO release.
include(FetchContent)
if (WIN32)
    set(DynamoRIO_URL "https://github.com/DynamoRIO/dynamorio/releases/download/release_9.0.1/DynamoRIO-Windows-9.0.1.zip")
endif (WIN32)
if (UNIX)
    set(DynamoRIO_URL "https://github.com/DynamoRIO/dynamorio/releases/download/release_9.0.1/DynamoRIO-Linux-9.0.1.tar.gz")
endif (UNIX)
if ("${DynamoRIO_URL}" STREQUAL "")
	message(FATAL_ERROR "Your OS is currently not supported by DynamoRIO.")
endif()
message("Downloading DynamoRIO from ${DynamoRIO_URL}...")
FetchContent_Declare(
  dynamorio
  URL ${DynamoRIO_URL}
)
FetchContent_MakeAvailable(dynamorio)
FetchContent_GetProperties(dynamorio SOURCE_DIR DynamoRIO_ROOT)
FILE(TO_CMAKE_PATH "${DynamoRIO_ROOT}/cmake" DynamoRIO_DIR)
message("Using DynamoRIO_DIR=${DynamoRIO_DIR} for build...")

# Load DynamoRIO config from DynamoRIO_DIR/cmake/DynamoRIOConfig.cmake.in
find_package(DynamoRIO)
if (NOT DynamoRIO_FOUND)
    message(FATAL_ERROR "DynamoRIO package required to build")
endif(NOT DynamoRIO_FOUND)