# define source files
set(app_SRCS main.cpp)

# define target
add_executable(app ${app_SRCS})

# link dependent libraries
target_link_libraries(app
        libfoo
        libbar
        )