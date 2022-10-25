#include "dr_api.h"
#include <iostream>
#include <string>
#include <cassert>

#include "extractor.h"

static void
initOptions(int argc, const char* argv[], FunctionExtractorOptions& opts)
{
    std::string token;

    opts.debug = false;
    opts.sourcePattern = ".*";

    bool foundInput = false;

    for (int i = 1; i < argc; i++) {
        token = argv[i];
        if (token.compare("-input") == 0) {
            assert(("Missing input binary file", (i + 1) < argc));
            opts.file = argv[++i];
            foundInput = true;
        }
        if (token.compare("-sources") == 0) {
            assert(("Missing source pattern", (i + 1) < argc));
            opts.sourcePattern = argv[++i];
        }
        else if (token.compare("-debug") == 0) {
            opts.debug = true;
        }
    }
    if (!foundInput || !fs::exists(opts.file)) {
        printf("Missing input file.\n");
        exit(1);
    }
}

/**
 * The BinaryRTS extractor is a simple program that extracts all functions from a binary.
 */
int
main(int argc, const char* argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);
    try {
        dr_standalone_init();
        FunctionExtractorOptions opts;
        initOptions(argc, argv, opts);
        std::cout
            << "Called BinaryRTS function extractor with options:\n"
            << "-input: " << opts.file << "\n"
            << "-sources: " << opts.sourcePattern << std::endl;
        FunctionExtractor extractor{ opts };
        extractor.extractFunctions();
        dr_standalone_exit();
    }
    catch (std::exception& ex) {
        std::cerr << ex.what() << std::endl;
    }
    catch (...) {
        std::cerr << "Caught unknown exception." << std::endl;
    }
    return 0;
}