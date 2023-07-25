#pragma once

#include <string>
#include <filesystem>
#include <memory>
#include <optional>
#include <regex>
#include <unordered_map>
#include <unordered_set>
#include <set>

namespace fs = std::filesystem;

// Basic types for lines and symbols.
using Line = uint64_t;
using Offset = size_t;

struct CoveredLine {
    std::string file;
    Line line;
    Offset offset;
};

// A cache to keep track of covered lines and BBs.
struct LineCache {

    explicit LineCache(bool queryMissingOffsets = false): queryMissingOffsets(queryMissingOffsets) {}

    // A line map keeps track of lines' offsets and the corresponding line information.
    using LineMap = std::unordered_map<Offset, std::unique_ptr<CoveredLine>>;

    // A fast-lookup module map keeps track of modules (by name) and their corresponding lines.
    using ModuleLineMap = std::unordered_map<std::string, LineMap>;

    // A module map keeps track of modules (by name) and all line offsets (ordered -> O(log(N) complexity) .
    using ModuleOffsetMap = std::unordered_map<std::string, std::set<Offset>>;

    // A module BB map keeps track of modules (by name) and all BB offsets that have already been queried.
    using ModuleBBMap = std::unordered_map<std::string, std::unordered_set<Offset>>;

    CoveredLine *findLine(const std::string &moduleName, Offset offset);

    [[nodiscard]] bool hasRecordedBB(const std::string &moduleName, Offset offset) {
        return modulesBBs[moduleName].count(offset) != 0;
    }

    void recordBB(const std::string &moduleName, Offset offset) {
        modulesBBs[moduleName].insert(offset);
    }

    [[nodiscard]] bool hasModule(const std::string &moduleName) const noexcept {
        return modulesLines.count(moduleName) != 0;
    };

    CoveredLine *addLine(const std::string &moduleName, CoveredLine &&coveredLine);

private:
    ModuleLineMap modulesLines;
    ModuleOffsetMap modulesOffsets;
    ModuleBBMap modulesBBs;
    bool queryMissingOffsets = false;
};

// Line coverage container.
// Maps filenames to a pair of <covered,uncovered> lines.
using LineCoverage = std::unordered_map<std::string, std::pair<std::unordered_set<Line>, std::unordered_set<Line>>>;

// Visualizer CLI options.
struct VisualizerOptions {
    std::string ext;
    std::string regex;
    fs::path root;
    bool debug;
    bool queryMissingOffsets;
};

// Visualizer orchestration class.
class Visualizer {
public:
    explicit Visualizer(const VisualizerOptions &options) : options{options}, isInitialized{false} {
        if (!options.regex.empty()) {
            regex.emplace(std::regex(options.regex));
        }
        lineCache = LineCache{options.queryMissingOffsets};
    }

    void run();

private:
    void initSymbolServer();

    void cleanupSymbolServer();

    void walkCoverageFiles();

    void analyzeCoverageFile(const fs::path &file);

    void writeLCOVFile(const fs::path &file);

    void addModuleLines(const std::string &moduleName, const fs::path &modulePath);

    LineCoverage lineCoverage;
    LineCache lineCache;
    const VisualizerOptions options;
    std::optional<std::regex> regex;
    bool isInitialized;
};