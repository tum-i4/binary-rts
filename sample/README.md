# BinaryRTS Sample Project

This project aims to demonstrate how BinaryRTS can be used in a C++ (GoogleTest) project.

## Prerequisites

- [BinaryRTS DynamoRIO instrumentation client](../binaryrts/client) has been built
- [BinaryRTS CLI](../binaryrts/cli) has been built and `binaryrts` is in `PATH`

## Build

To build the project, use `cmake` (see build description [here](../README.md)).
In fact, this sample project will be built if you run the `cmake` build in the root of the BinaryRTS repository.

Note that ideally you want to use a debug build (or release build with function inlining deactivated) for the most
precise coverage.

## Run

Note: The following commands assume that you are in the root of the BinaryRTS repository.

### Executing Tests without Instrumentation

```shell
$ build/sample/tests/unittests
``` 

### Executing Tests with BinaryRTS Instrumentation

```shell
# [Optional] Only instrument the "unittests" binary.
$ echo "unittests" > modules.txt
# Optionally, you can disable following child processes (recommended) and disable DynamoRIO trace creation (sometimes faster)
$ build/_deps/dynamorio-src/bin64/drrun [-no_follow_children] [-disable_traces] -c build/binaryrts/client/libbinary_rts_client.so -modules modules.txt -logdir unittests -runtime_dump -syscalls -- build/sample/tests/unittests
``` 

### Creating Test Traces from Raw Coverage with CLI

Covered functions for each test:
````shell
# By default, test traces are generated in current working directory (can be changed with -o)
$ binaryrts convert -i unittests --regex ".*sample.*" --repo . cpp --symbols --resolver build/binaryrts/resolver/binary_rts_resolver
$ ls -la | grep ".csv"
-rw-r--r--   1 root root  3652 Oct 24 10:43 function-lookup.csv
-rw-r--r--   1 root root  1257 Oct 24 10:43 test-function-traces.csv
-rw-r--r--   1 root root  2421 Oct 24 10:43 test-lookup.csv
````

Accessed files for each test:
````shell
# By default, test traces are generated in current working directory (can be changed with -o)
$ binaryrts convert -i unittests --repo . syscalls
$ ls -la | grep ".csv"
-rw-r--r--   1 root root  3652 Oct 24 10:43 function-lookup.csv
-rw-r--r--   1 root root    41 Oct 24 11:50 test-file-traces.csv
-rw-r--r--   1 root root  1257 Oct 24 10:43 test-function-traces.csv
-rw-r--r--   1 root root  2421 Oct 24 10:43 test-lookup.csv
````

### Make Some Changes to Sample Project

```diff
diff --git a/sample/tests/testfoo.cpp b/sample/tests/testfoo.cpp
index 9edca4f..e999a8d 100644
--- a/sample/tests/testfoo.cpp
+++ b/sample/tests/testfoo.cpp
@@ -46,7 +46,7 @@ TEST_F(FooTest, SometimesBazFalseIsTrue) {

 // simple test
 TEST(FooTestSuite, AlwaysTrue) {
-    ASSERT_EQ(true, true);
+    ASSERT_EQ(true, false);
 }

 // simple test with long name
```

And commit the changes:
```shell
$ git add sample/tests/testfoo.cpp
$ git commit -m "Update FooTestSuite"
```

### Run Test Selection with CLI

```shell
# Run fastest (least safe) test selection without any over-approximations for safety
$ binaryrts select -f HEAD~1 -t HEAD --repo . cpp --lookup function-lookup.csv --traces test-function-traces.csv
# Check the selected tests (you can also check `excluded.txt` for all excluded tests)
$ cat included.txt
unittests!!!FooTestSuite!!!AlwaysTrue
```

### Run Only Selected Tests for Sample Project

```shell
$ export GTEST_EXCLUDES_FILE=$(pwd)/excluded.txt
$ build/sample/tests/unittests
``` 