#include "dr_api.h"
#include <iostream>
#include <string>
#include <cassert>

#include "extractor.h"


namespace {
    ExtractorOptions
    parseArgs(int argc, const char *argv[]) {
        ExtractorOptions opts;
        opts.debug = false;
        opts.sourcePattern = ".*";
        opts.mode = ExtractorMode::LINES;

        std::string token;
        bool foundInput = false;

        for (int i = 1; i < argc; i++) {
            token = argv[i];
            if (token == "-input") {
                assert(("Missing input binary file", (i + 1) < argc));
                opts.file = argv[++i];
                foundInput = true;
            } else if (token == "-regex") {
                assert(("Missing source regex pattern", (i + 1) < argc));
                opts.sourcePattern = argv[++i];
            } else if (token == "-mode") {
                assert(("Missing mode", (i + 1) < argc));
                std::string mode = argv[++i];
                if (mode == "symbols") {
                    opts.mode = ExtractorMode::SYMBOLS;
                }
            } else if (token == "-debug") {
                opts.debug = true;
            }
        }
        if (!foundInput || !fs::exists(opts.file)) {
            std::cerr << "Missing valid input file." << std::endl;
            exit(1);
        }
        return opts;
    }
}


/**
 * The BinaryRTS extractor is a simple program that extracts source line information for all
 * functions or lines from a binary.
 */
int
main(int argc, const char *argv[]) {
    setvbuf(stdout, nullptr, _IONBF, 0);
    try {
        dr_standalone_init();
        ExtractorOptions opts = parseArgs(argc, argv);
        std::cout
                << "Called BinaryRTS function extractor with options:\n"
                << "-input: " << opts.file << "\n"
                << "-mode: " << (opts.mode == ExtractorMode::LINES ? "lines" : "symbols") << "\n"
                << "-regex: " << opts.sourcePattern << std::endl;
        SourceLineExtractor extractor{opts};
        extractor.extractSourceLines();
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