# BinaryRTS JUnit5 Test Listener

This project is a simple test listener for JUnit (example for JUnit5 below) in case one wants to instrument binaries
loaded by JUnit tests.
The test listener simply enables you to attach the BinaryRTS client to your running JVM process when the test suite is
first loaded.
Therefore, the test listener allows defining a pre-test command that should contain your logic of attaching to the JVM
process (see example below).

## Install Test Listener to Local Maven Repository

```shell
$ mvn clean install
```

## Use in Maven Surefire JUnit5 Project

The JUnit test listener is packaged as a Java agent that can be attached to any JVM by using
the `-javaagent:/path/to/agent.jar` JVM runtime option.
For instance, if you want to use the agent inside a Maven Surefire project that uses JUnit5 (and forks each test suite
into its own JVM), you can simply add the following to your Maven command:

```shell
# Unix-like
$ mvn clean test -fn -Dmaven.surefire.debug="-javaagent:/path/to/.m2/repository/edu/tum/sse/binaryrts/junit-test-listener/1.0-SNAPSHOT/junit-test-listener-1.0-SNAPSHOT.jar=rts.cmd='echo BINARY_RTS_PID > BINARY_RTS_PRE_TEST_SYNC_FILE',rts.out=$(pwd)" -DforkCount=1 -DreuseForks=false
# Windows
$ mvn clean test -fn -Dmaven.surefire.debug="-javaagent:c:\path\to\.m2\repository\edu\tum\sse\binaryrts\junit-test-listener\1.0-SNAPSHOT\junit-test-listener-1.0-SNAPSHOT.jar=rts.cmd='echo BINARY_RTS_PID > BINARY_RTS_PRE_TEST_SYNC_FILE',rts.out=%cd%" -DforkCount=1 -DreuseForks=false
```

### Options

To set up the agent that is attached to a JVM via `-javaagent:/path/to/agent.jar`, several runtime options can be
provided as key value pairs `-javaagent:/path/to/agent.jar=key1=val1,key2=val2,...`:

| Key          | Type    | Default value                          | Description                                                                      |
|--------------|---------|----------------------------------------|----------------------------------------------------------------------------------|
| rts.out      | String  | `.`                                    | Output path for agent output                                                     |
| rts.sync     | Boolean | `false`                                | Enables sync (JVM process will wait for pre-test command to create sync file)    |
| rts.cmd      | String  | `null`                                 | The pre-test command that is executed by the agent before any testing is started |

### Environment Variables inside Pre-test Command

- `BINARY_RTS_PID`: The process identifier (PID) of the JVM process that executes the tests (e.g., to attach to it)
- `BINARY_RTS_PRE_TEST_SYNC_FILE`: The absolute file path of the sync file; if `rts.sync` is provided (or set to `true`)
  , the JVM will block until the pre-test command has created this file in the filesystem

## Example for Attaching BinaryRTS DR client

```shell
# Windows
$ mvn clean test -fn -D"maven.surefire.debug"="-Djava.compiler=NONE -Xint -javaagent:C:\path\to\.m2\repository\edu\tum\sse\binaryrts\junit-test-listener\1.0-SNAPSHOT\junit-test-listener-1.0-SNAPSHOT.jar=rts.cmd='C:\path\to\workspace\binary-rts\out\build\x64-Release\_deps\dynamorio-src\bin64\drrun.exe -attach BINARY_RTS_PID -c C:\path\to\workspace\binary-rts\out\build\x64-Release\binaryrts\client\binary_rts_client.dll -output BINARY_RTS_PRE_TEST_SYNC_FILE',rts.out=%cd%" -DforkCount=1 -DreuseForks=false
```
