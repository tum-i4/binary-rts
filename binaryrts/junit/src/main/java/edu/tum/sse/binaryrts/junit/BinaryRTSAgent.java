package edu.tum.sse.binaryrts.junit;

import java.io.IOException;
import java.lang.instrument.Instrumentation;
import java.nio.file.Files;

public class BinaryRTSAgent {

    private static int agentCount = 0;

    public static void premain(String arguments, Instrumentation instrumentation) throws IOException {
        if (agentCount > 0) {
            return;
        }
        AgentOptions options = AgentOptions.fromString(arguments);
        System.err.println("Attaching agent (" + agentCount++ + ") to PID " + BinaryRTSHelper.CURRENT_PID + " with args: " + options);
        Files.createDirectories(options.getOutputDirectory());
        BinaryRTSHelper.outputDirectory = options.getOutputDirectory();
        BinaryRTSHelper.preTestCommand = options.getCommand();
        BinaryRTSHelper.syncCommand = options.shouldSyncCommand();
        BinaryRTSHelper.startPreTestHook();
    }
}
