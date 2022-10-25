# BinaryRTS DynamoRIO Client

BinaryRTS implements a custom DynamoRIO client that collects coverage, and (optionally) listens to custom events that can be emitted by the system under test (so-called [annotations](https://dynamorio.org/using.html#sec_annotations)).
This way, it enables dumping coverage during runtime, whenever a custom event is emitted.
Parts of the code are copied and modified from [`drcov`](https://dynamorio.org/page_drcov.html), DynamoRIO's coverage tool.

## BinaryRTS Coverage Client Options

Currently, the BinaryRTS client supports the following options:

- `-symbols`: By default, BinaryRTS only outputs the covered BB offsets. Adding this flag will enable resolving symbols of covered offsets (filepath and line number).
- `-runtime_dump`: Allows dumping coverage during runtime (using [annotations](https://dynamorio.org/using.html#sec_annotations)).
- `-text_dump`: Output a text coverage dump of covered BB offsets, instead of binary dump.
- `-syscalls`: Enables tracing opened files. Defaults to output files with `*.log.syscalls`.
- `-verbose [uint]`: Controls the verbosity of logging. By default, verbosity is `0`, whereas larger values will result in more verbose logging.
- `-logdir [path]`: Sets the output directory of coverage dumps (use absolute paths!). Defaults to `.`, i.e., current working directory.
- `-modules [path]`: Allows to provide a file containing the names of modules to be instrumented. The file should simply contain a newline-separated list of module names. If none is provided, all modules will be instrumented.
- `-output [name]`: Set the output file name that will contain the dumped coverage information. Defaults to `coverage.log`.

## Running the sample project

To run the unit tests of the included sample project, invoke it as follows (shown for Windows and `Release` build here):
```bash
build\_deps\dynamorio-src\bin64\drrun.exe -c build\binaryrts\client\Release\binary_rts_client.dll -output cov.log -symbols -- build\sample\tests\Release\unittests.exe
```

## Profiling the Coverage Client

We have successfully profiled the client using `perf` on Linux (may require `sudo`):

```shell
mkdir build
cd build
cmake ..
make
perf record build/_deps/dynamorio-src/bin64/drrun -c build/binaryrts/client/libbinary_rts_client.so -- build/sample/tests/unittests
# analyze hot modules
perf report --stdio --sort comm,dso -f
# analyze hot functions in client
perf report --stdio --dsos=naive,libbinary_rts_client.so -f
```