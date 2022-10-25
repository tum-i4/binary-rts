package edu.tum.sse.binaryrts.junit;

import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

public class BinaryRTSHelper {

    public static final String CURRENT_PID = java.lang.management.ManagementFactory.getRuntimeMXBean().getName().split("@")[0];
    /**
     * The name of the lookup file into which the mapping (dump ID, test suite name) is written.
     */
    public static final String TEST_IDENTIFIER_LOOKUP_FILE = "dump-lookup.log";
    /**
     * The dump identifier for the current test JVM.
     */
    public static final String DUMP_ID = CURRENT_PID + "_" + System.currentTimeMillis();
    /**
     * Key of the environment variable that contains the file path to the sync file.
     * The JVM process executing the pre-test command will block until the sync file is available if `syncCommand` is `true`.
     */
    private static final String PRE_TEST_HOOK_SYNC_KEY = "BINARY_RTS_PRE_TEST_SYNC_FILE";
    /**
     * This environment variable will be set on the created process for the pre-test hook.
     */
    private static final String PID_KEY = "BINARY_RTS_PID";
    /**
     * Whether to execute the pre-test command synchronously.
     * This causes the command execution to block the JVM process and
     * wait until the sync file available.
     */
    public static boolean syncCommand;
    /**
     * The output directory where to store artifacts.
     */
    public static Path outputDirectory;
    /**
     * The pre-test command that will be executed before any test is run.
     */
    public static String preTestCommand;
    /**
     * Time delta in milliseconds for maximum wait period before continuing when in sync mode.
     */
    private static final long MAX_SYNC_WAIT_TIME = 60_000;
    private static boolean preTestHookExecuted = false;

    public static String wrapEnvironmentVariable(String command, String envVar) {
        if (isWindows()) {
            return command.replaceAll("([^%])(" + envVar + ")", "$1%$2%");
        } else {
            return command.replaceAll("([^${])(" + envVar + ")", "$1\\$\\{$2\\}");
        }
    }

    public static void startPreTestHook() {
        if (preTestHookExecuted) {
            System.err.println("Pre-test hook already executed, skipping.");
            return;
        }

        if (preTestCommand == null || preTestCommand.isEmpty()) {
            System.err.println("No pre-test command specified.");
            return;
        }

        try {
            List<String> command;
            preTestCommand = wrapEnvironmentVariable(preTestCommand, PID_KEY);
            preTestCommand = wrapEnvironmentVariable(preTestCommand, PRE_TEST_HOOK_SYNC_KEY);
            if (isWindows()) {
                command = Arrays.asList("cmd", "/c", preTestCommand);
            } else {
                command = Arrays.asList("bash", "-c", preTestCommand);
            }
            ProcessBuilder processBuilder = new ProcessBuilder(command);
            Map<String, String> env = processBuilder.environment();
            env.put(PID_KEY, CURRENT_PID);
            Path syncFile = outputDirectory.resolve(String.format("%s.log", DUMP_ID)).toAbsolutePath();
            env.put(PRE_TEST_HOOK_SYNC_KEY, syncFile.toString());
            System.err.println("Running pre-test command (" + CURRENT_PID + "): " + command);
            processBuilder.start();
            // In case sync file is set, we continue once the file actually exists
            // (simple IPC to keep this JVM process blocked).
            if (syncCommand) {
                long before = System.currentTimeMillis();
                while (!(syncFile.toFile().exists() || (System.currentTimeMillis() - before) > MAX_SYNC_WAIT_TIME)) {
                    System.err.println("Waiting for syncFile at: " + syncFile);
                    Thread.sleep(1_000);
                }
            }
            preTestHookExecuted = true;
        } catch (Exception e) {
            System.err.println("Failed to start pre-test hook: " + e.getMessage());
            e.printStackTrace();
        }
    }

    private static boolean isWindows() {
        return System.getProperty("os.name").toLowerCase().contains("win");
    }

}
