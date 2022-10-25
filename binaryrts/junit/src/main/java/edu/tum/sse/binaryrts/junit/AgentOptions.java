package edu.tum.sse.binaryrts.junit;

import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.AbstractMap;
import java.util.Map;
import java.util.stream.Collectors;
import java.util.stream.Stream;

public class AgentOptions {
    private static final String COMMAND_KEY = "rts.cmd";
    private static final String OUTPUT_KEY = "rts.out";
    private static final String SYNC_KEY = "rts.sync";
    private static final String OPTIONS_SEPARATOR = ",";
    private static final String VALUE_SEPARATOR = "=";

    private String command = "";
    private Path outputDirectory = Paths.get("");
    private boolean syncCommand = false;

    public AgentOptions() {
    }

    public static AgentOptions fromString(final String options) {
        final AgentOptions result = new AgentOptions();
        final Map<String, String> optionsInput = extractOptions(options);
        result.outputDirectory = Paths.get(optionsInput.getOrDefault(OUTPUT_KEY, String.valueOf(result.outputDirectory))).toAbsolutePath();
        result.command = optionsInput.getOrDefault(COMMAND_KEY, String.valueOf(result.command));
        result.syncCommand = Boolean.parseBoolean(optionsInput.get(SYNC_KEY));
        return result;
    }

    private static Map<String, String> extractOptions(String options) {
        if (options == null) {
            options = "";
        }
        return Stream.of(options.split(OPTIONS_SEPARATOR))
                .map(String::trim)
                .filter(part -> !part.isEmpty())
                .map(
                        part -> {
                            final int eqIndex = part.indexOf(VALUE_SEPARATOR);
                            if (eqIndex > 0) {
                                return new AbstractMap.SimpleEntry<>(
                                        part.substring(0, eqIndex), part.substring(eqIndex + 1).replaceAll("^\"|\"$", "").replaceAll("^'|'$", ""));
                            }
                            // We also allow boolean flags, if only a key is provided.
                            return new AbstractMap.SimpleEntry<>(part, "true");
                        })
                .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));
    }

    public String getCommand() {
        return command;
    }

    public Path getOutputDirectory() {
        return outputDirectory;
    }

    public boolean shouldSyncCommand() {
        return syncCommand;
    }

    @Override
    public String toString() {
        return "AgentOptions{" +
                "command='" + command + '\'' +
                ", outputDirectory=" + outputDirectory +
                ", syncCommand=" + syncCommand +
                '}';
    }
}
