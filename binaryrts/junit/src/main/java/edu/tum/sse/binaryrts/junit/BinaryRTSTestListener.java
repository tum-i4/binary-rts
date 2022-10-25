package edu.tum.sse.binaryrts.junit;

import org.junit.platform.engine.TestExecutionResult;
import org.junit.platform.engine.TestSource;
import org.junit.platform.engine.support.descriptor.ClassSource;
import org.junit.platform.engine.support.descriptor.MethodSource;
import org.junit.platform.launcher.TestExecutionListener;
import org.junit.platform.launcher.TestIdentifier;
import org.junit.platform.launcher.TestPlan;
import org.junit.runner.Description;
import org.junit.runner.Result;
import org.junit.runner.notification.RunListener;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

public class BinaryRTSTestListener extends RunListener implements TestExecutionListener {

    private boolean testSuiteInitialized = false;
    private String testId = "";
    private boolean hasWrittenDumpId = false;

    public BinaryRTSTestListener() {
        System.err.println("Starting BinaryRTS per-test listener...");
    }

    @Override
    public void executionStarted(TestIdentifier testIdentifier) {
        if (!testSuiteInitialized && testIdentifier != null) {
            Description description = convertTestIdentifierToDescription(testIdentifier);
            if (testIdentifier.isTest() && description != null) {
                testId = description.getClassName();
                System.err.println("Test " + testId + " has dump identifier " + BinaryRTSHelper.DUMP_ID);
                testSuiteInitialized = true;
            }
        }
    }

    @Override
    public void testStarted(final Description testDescription) {
        if (!testSuiteInitialized && testDescription != null) {
            testId = testDescription.getClassName();
            testSuiteInitialized = true;
        }
    }

    @Override
    public void testPlanExecutionFinished(final TestPlan testPlan) {
        writeLookupFile();
    }

    @Override
    public void testRunFinished(final Result result) throws Exception {
        writeLookupFile();
    }

    private void writeLookupFile() {
        if (testSuiteInitialized && !testId.isEmpty() && !hasWrittenDumpId) {
            try {
                Path lookupFile = BinaryRTSHelper.outputDirectory.resolve(BinaryRTSHelper.TEST_IDENTIFIER_LOOKUP_FILE).toAbsolutePath();
                Files.write(
                        lookupFile,
                        String.format("%s;%s\n", BinaryRTSHelper.DUMP_ID, testId).getBytes(),
                        StandardOpenOption.CREATE, StandardOpenOption.APPEND);
                hasWrittenDumpId = true;
            } catch (Exception e) {
                System.err.println("Failed to write lookup file: " + e.getMessage());
            }
        }
    }

    /**
     * We must convert the JUnit5 {@link TestIdentifier} to a JUnit4-compatible description format {@link Description}.
     * This method will return `null` in case the test identifier is neither a test suite nor a test method.
     */
    private Description convertTestIdentifierToDescription(final TestIdentifier testIdentifier) {
        // [engine:junit-vintage/jupiter] containers will not have a parent and are excluded
        if (!testIdentifier.getParentId().isPresent()) {
            return null;
        }

        if (!testIdentifier.getSource().isPresent()) {
            return null;
        }
        final TestSource source = testIdentifier.getSource().get();

        // we only count containers as test suites that are classes
        // parameterized test methods are excluded by returning null here
        if (!(testIdentifier.isTest()) && !(source instanceof ClassSource)) {
            return null;
        }

        // a test that does not have a method source is ignored
        if (testIdentifier.isTest() && !(source instanceof MethodSource)) {
            return null;
        }

        if (testIdentifier.isTest()) {
            final MethodSource methodSource = (MethodSource) source;
            final String className = methodSource.getClassName();
            return Description.createTestDescription(className, testIdentifier.getDisplayName(), testIdentifier.getUniqueId());
        }
        return Description.createSuiteDescription(testIdentifier.getDisplayName(), testIdentifier.getUniqueId());
    }
}
