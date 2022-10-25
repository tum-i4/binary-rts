# BinaryRTS

BinaryRTS is an RTS tool based on dynamic binary instrumentation.
A sample project and instructions on how to use BinaryRTS can be found [here](./sample).

## Structure

The project has the following structure:

```
├── binaryrts       <- BinaryRTS sources.
│   ├── client      <- Dynamic binary instrumentation client for DynamoRIO.
│   ├── cli         <- BinaryRTS CLI for test trace conversion and running the test selection.
│   ├── extractor   <- C/C++ function extractor from binaries for Frida agent (Windows-only, experimental).
│   ├── frida       <- Dynamic binary instrumentation agent using Frida (experimental).
│   ├── junit       <- JUnit test listener that can be used to attach BinaryRTS to Java tests.
│   ├── listener    <- C++ test event listener to regularly dump coverage during test execution (e.g., with GoogleTest).
│   └── resolver    <- C/C++ symbol resolver based on DynamoRIO's symbol access library.
├── cmake           <- Internal cmake configuration files.
├── sample          <- Sample GoogleTest project to experiment with BinaryRTS.
└── scripts         <- Scripts and utilities to set up BinaryRTS (e.g., patch GoogleTest main routines). 
```

## Build

### CMake

Except for the [BinaryRTS CLI](./binaryrts/cli) project, all parts of BinaryRTS can be built using `cmake`.
Run the following commands in the root of the BinaryRTS repository, to build all subprojects:

```shell
mkdir build
cd build
# (1) Generate build system using cmake
# Linux/Windows
cmake -DCMAKE_BUILD_TYPE=Debug ..
# [optional] Change generator and target arch on Windows (currently requires MSVC toolchain v142)
cmake -DCMAKE_BUILD_TYPE=Debug -G "Visual Studio 16 2019" -A x64 ..
cmake -DCMAKE_BUILD_TYPE=Debug -G "Visual Studio 17 2022" -A x64 ..
# (2) Build BinaryRTS using generated build system (Win32: MSBuild, Linux: Unix Makefiles)
cmake --build . --config Debug
```

### Docker

There is a [`Dockerfile`](./Dockerfile.dev) for dockerized builds, e.g., on platforms other than Linux/Windows such
as macOS.
For building the Docker image and creating a container with a new `bash` session, run:

```shell
# Build BinaryRTS docker image 
$ docker build -t binaryrts:1.0 -f Dockerfile.dev .
# Create and run container with new bash session and current working directory mounted into container
$ docker run -v $(pwd):/binary-rts -it binaryrts:1.0 bash
```

Then, you can run the `cmake` commands from above inside the `bash` session to build BinaryRTS.
