#pragma once

#include <filesystem>
#include <vector>
#include <regex>
#include <unordered_map>

namespace fs = std::filesystem;

enum class ExtractorMode {
    LINES,
    SYMBOLS
};

struct ExtractorOptions {
    fs::path file;
    std::string sourcePattern;
    bool debug;
    ExtractorMode mode;
};

struct SourceLine {
    std::string name;
    std::string file;
    uint64_t line;
    size_t offset;
};

using SourceLines = std::vector<SourceLine>;
using OffsetMap = std::unordered_map<size_t, SourceLine>;

class SourceLineExtractor {
public:
    explicit SourceLineExtractor(const ExtractorOptions& options) : options{options},
                                                                    sourcePattern{options.sourcePattern} {
    }

    void extractSourceLines();

private:
    void initSymbolServer();

    void cleanupSymbolServer();

    OffsetMap extractAllSourceLines();

    SourceLines filterSourceLinesForSymbols(OffsetMap& sourceLinesOffsetMap);

    void writeSourceLinesToOutput(const SourceLines &sourceLines);

    const ExtractorOptions options;
    const std::regex sourcePattern;
    bool isInitialized = false;
};