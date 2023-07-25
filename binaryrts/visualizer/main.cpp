#include "dr_api.h"
#include <iostream>
#include <string>
#include <cassert>

#include "visualizer.h"

static void
initOptions(int argc, const char *argv[], VisualizerOptions &opts) {
    std::string token;

    /* Default values. */
    opts.ext = ".log";
    opts.regex = "";
    opts.root = ".";
    opts.debug = false;
    opts.queryMissingOffsets = false;

    for (int i = 1; i < argc; i++) {
        token = argv[i];
        if (token == "-ext") {
            assert(("Missing extension", (i + 1) < argc));
            opts.ext = argv[++i];
        } else if (token == "-regex") {
            assert(("Missing regex", (i + 1) < argc));
            opts.regex = argv[++i];
        } else if (token == "-root") {
            assert(("Missing root directory", (i + 1) < argc));
            opts.root = argv[++i];
        } else if (token == "-debug") {
            opts.debug = true;
        } else if (token == "-accurate") {
            opts.queryMissingOffsets = true;
        }
    }
}

/**
 * The BinaryRTS visualizer is a simple program that resolves symbols for offset addresses of covered modules
 * and outputs an LCOV coverage report.
 */
int
main(int argc, const char *argv[]) {
    setvbuf(stdout, nullptr, _IONBF, 0);
    try {
        dr_standalone_init();
        VisualizerOptions opts;
        initOptions(argc, argv, opts);
        std::cout
                << "Called BinaryRTS visualizer with options:\n"
                << "-ext: " << opts.ext << "\n"
                << "-regex: " << opts.regex << "\n"
                << "-root: " << opts.root << std::endl;
        Visualizer visualizer{opts};
        visualizer.run();
        dr_standalone_exit();
    }
    catch (std::exception &ex) {
        std::cerr << ex.what() << std::endl;
    }
    catch (...) {
        std::cerr << "Caught unknown exception." << std::endl;
    }
    return 0;
}
