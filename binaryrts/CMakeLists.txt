cmake_minimum_required(VERSION 3.14)

add_subdirectory(client)
add_subdirectory(resolver)
add_subdirectory(listener)
add_subdirectory(visualizer)

if (WIN32)
    add_subdirectory(extractor)
endif (WIN32)
