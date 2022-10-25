#pragma once

#include <filesystem>
#include <vector>
#include <regex>

namespace fs = std::filesystem;

// FunctionExtractor CLI options.
struct FunctionExtractorOptions {
    fs::path file;
    std::string sourcePattern;
    bool debug;
};

struct FunctionDefinition {
    std::string name;
    std::string file;
    uint64_t line;
    size_t offset;
};

using FunctionDefinitions = std::vector<FunctionDefinition>;

class FunctionExtractor {
public:
    explicit FunctionExtractor(const FunctionExtractorOptions& options) : options{ options } {
        sourcePattern = std::regex(options.sourcePattern);
    }

    void extractFunctions();

private:
    void initSymbolServer();
    void cleanupSymbolServer();

    void writeFunctions(const FunctionDefinitions& functions);

    const FunctionExtractorOptions& options;
    std::regex sourcePattern;
    bool isInitialized = false;
};