#include "dr_api.h"
#include "drsyms.h"
#include <chrono>
#include <filesystem>

#include "visualizer.h"

// Keep as macro for convenient usage in format string.
#define NON_FILE_PATH_SEP "\t"

namespace {
    const char *DUMP_LOOKUP_FILE = "dump-lookup.log";
    const size_t MAX_SYM_RESULT = 256;
    const size_t MAX_LINE_LENGTH = 512;
}

namespace fs = std::filesystem;

CoveredLine *LineCache::findLine(const std::string &moduleName, Offset offset) {
    LineMap *lineMap = &modulesLines[moduleName];
    // Prevent calling hashing function of moduleName multiple times.
    auto lineIt = lineMap->find(offset);
    if (lineIt != lineMap->end()) {
        return lineIt->second.get();
    }
    // If we reach this point, the BB's start or end offset is inside a line (not the beginning of a line).
    // Approach 1 (slow): query the symbol API again for this offset.
    if (queryMissingOffsets) {
        char file[MAXIMUM_PATH];
        char name[MAX_SYM_RESULT];
        drsym_error_t symres;
        drsym_info_t sym;
        sym.struct_size = sizeof(sym);
        sym.name = name;
        sym.name_size = MAX_SYM_RESULT;
        sym.file = file;
        sym.file_size = MAXIMUM_PATH;
        symres = drsym_lookup_address(
                moduleName.c_str(),
                offset,
                &sym,
                DRSYM_DEFAULT_FLAGS
        );
        if (symres == DRSYM_SUCCESS) {
            // Create new covered line entry and add to map.
            auto &entry = (*lineMap)[offset];
            entry = std::make_unique<CoveredLine>();
            entry->offset = offset;
            entry->file = file;
            entry->line = sym.line;
            modulesOffsets[moduleName].insert(offset);
            return entry.get();
        } else {
            return nullptr;
        }
    } else {
        // Approach 2 (fast): we check the already recorded BBs to find the one at the beginning of the line
        // that precedes the current BB.
        auto &offsetMap = modulesOffsets[moduleName];
        auto it = offsetMap.upper_bound(offset);
        if (it == offsetMap.end() || it == offsetMap.begin()) {
            return nullptr;
        }
        Offset succeedingOffset = *it;
        Offset precedingOffset = *(--it);
        auto &precedingLine = (*lineMap)[precedingOffset];
        auto &succeedingLine = (*lineMap)[succeedingOffset];
        if (precedingLine->line != succeedingLine->line) {
            return nullptr;
        }
        // Create new covered line entry and add to map.
        auto &entry = (*lineMap)[offset];
        entry = std::make_unique<CoveredLine>();
        entry->offset = offset;
        entry->file = precedingLine->file;
        entry->line = precedingLine->line;
        // Make sure we mark the offset as already covered, for future queries.
        offsetMap.insert(offset);
        return entry.get();
    }
}

CoveredLine *LineCache::addLine(const std::string &moduleName, CoveredLine &&coveredLine) {
    LineMap *lineMap = &modulesLines[moduleName];
    auto &entry = (*lineMap)[coveredLine.offset];
    if (entry) {
        return entry.get();
    }
    entry = std::make_unique<CoveredLine>(coveredLine);
    auto &offsetMap = modulesOffsets[moduleName];
    offsetMap.insert(entry->offset);
    return entry.get();
}

struct EnumerateLinesCtx {
    LineCache *const cache;
    LineCoverage *const coverage;
    const std::string &moduleName;
};

bool enumerateLinesCb(drsym_line_info_t *info, void *data) {
    auto *enumLinesCtx = static_cast<EnumerateLinesCtx *>(data);
    CoveredLine *coveredLine = enumLinesCtx->cache->addLine(enumLinesCtx->moduleName,
                                                            CoveredLine{std::string(info->file), info->line,
                                                                        info->line_addr});
    if (coveredLine == nullptr) return false;
    // This will add the file to the map, if not yet existing.
    auto &entry = (*enumLinesCtx->coverage)[coveredLine->file];
    entry.second.insert(coveredLine->line);
    return true;
}

void Visualizer::addModuleLines(const std::string &moduleName, const fs::path &modulePath) {
    EnumerateLinesCtx ctx{&lineCache, &lineCoverage, moduleName};
    drsym_error_t symres;
    symres = drsym_enumerate_lines(
            modulePath.string().c_str(),
            enumerateLinesCb,
            &ctx
    );
    if (symres != DRSYM_SUCCESS) {
        printf("ERROR: Failed to enumerate lines for module %s with error %d\n", modulePath.string().c_str(), symres);
    } else {
        printf("INFO: Successfully enumerated lines for module %s\n", modulePath.string().c_str());
    }
}

void
Visualizer::analyzeCoverageFile(const fs::path &file) {
    if (options.debug)
        printf("DEBUG: Analyzing coverage file %s\n", file.string().c_str());
    // Keep per-file (i.e., per test) vector of covered modules with covered symbols.
    bool cursorBelowModuleName = false;
    std::string currentModuleName;
    FILE *fp = fopen(file.string().c_str(), "rb");
    char buffer[MAX_LINE_LENGTH];
    while (fgets(buffer, MAX_LINE_LENGTH, fp)) {
        // We only consider the following scenario with -text_dump:
        // module.exe   C:/path/to/module.exe
        //  +0x52630    23
        //  ...
        // New module line detected.
        if (buffer[0] != '\t') {
            std::string line{buffer};
            std::size_t pathStartPos = line.find(NON_FILE_PATH_SEP);
            std::size_t lineEndPos = line.find('\n');
            if (pathStartPos != std::string::npos) {
                cursorBelowModuleName = true;
                std::string modulePath = line.substr(pathStartPos + 1, lineEndPos - pathStartPos - 1);
                currentModuleName = fs::path(modulePath).string();
                if (!lineCache.hasModule(currentModuleName)) {
                    addModuleLines(currentModuleName, modulePath);
                }
            }
        }
            // Now, we'll find a BB offset here (+0x...) followed by the size of the BB
        else if (cursorBelowModuleName) {
            std::string line{buffer};
            std::size_t offsetStartPos = line.find('+');
            std::size_t offsetEndPos = line.find(NON_FILE_PATH_SEP, offsetStartPos);
            Offset startOffset = std::strtoul(line.substr(offsetStartPos, offsetEndPos - offsetStartPos).c_str(),
                                              nullptr, 16);
            std::size_t bbSizeStartPos = offsetEndPos + 1;
            std::size_t bbSizeEndPos = line.find('\n');
            uint64_t bbSize = std::strtoul(line.substr(bbSizeStartPos, bbSizeEndPos - bbSizeStartPos).c_str(),
                                           nullptr, 10);
            Offset endOffset = startOffset + bbSize;
            if (!lineCache.hasRecordedBB(currentModuleName, startOffset)) {
                lineCache.recordBB(currentModuleName, startOffset);
                auto startLine = lineCache.findLine(currentModuleName, startOffset);
                auto endLine = lineCache.findLine(currentModuleName, endOffset);
                if (startLine == nullptr) continue;
                auto &fileCoverage = lineCoverage[startLine->file];
                for (auto i = startLine->line; endLine != nullptr && i <= endLine->line; ++i) {
                    auto erasedLines = fileCoverage.second.erase(i);
                    if (erasedLines > 0) {
                        fileCoverage.first.insert(i);
                    }
                }
            }
        }
    }

    fclose(fp);

    if (options.debug)
        printf("DEBUG: Finished processing %s\n", file.string().c_str());
}

void
Visualizer::initSymbolServer() {
    if (isInitialized) { return; }

    if (drsym_init(0) != DRSYM_SUCCESS) {
        printf("WARN: Failed to initialize symbol handler\n");
    } else {
        if (options.debug)
            printf("DEBUG: Successfully initialized symbol handler\n");
        isInitialized = true;
    }
}

void
Visualizer::cleanupSymbolServer() {
    if (isInitialized) {
        if (options.debug)
            printf("DEBUG: Done with symbol handler, cleaning up now...\n");
        drsym_exit();
        isInitialized = false;
    }
}

void
Visualizer::writeLCOVFile(const fs::path &file) {
    if (options.debug)
        printf("DEBUG: Starting to write LCOV file to %s\n", file.string().c_str());
    FILE *fp = fopen(file.string().c_str(), "wb+");
    for (const auto &linesForFile: lineCoverage) {
        if (regex.has_value() && !std::regex_match(linesForFile.first, regex.value()))
            continue;
        fprintf(fp, "SF:%s\n", linesForFile.first.c_str());
        // covered lines
        for (const auto &line: linesForFile.second.first) {
            fprintf(fp, "DA:%ld,%d\n", line, 1);
        }
        // uncovered lines
        for (const auto &line: linesForFile.second.second) {
            fprintf(fp, "DA:%ld,%d\n", line, 0);
        }
        fprintf(fp, "end_of_record\n");
    }
    fclose(fp);
    if (options.debug)
        printf("DEBUG: Done writing LCOV file\n");
}

void
Visualizer::walkCoverageFiles() {
    if (options.debug)
        printf("DEBUG: Searching for coverage files with extension %s in %s\n", options.ext.c_str(),
               options.root.string().c_str());

    for (const auto &path: fs::recursive_directory_iterator(options.root)) {
        if (path.path().extension() == options.ext &&
            path.path().filename() != DUMP_LOOKUP_FILE) {
            analyzeCoverageFile(path.path());
        }
    }

    writeLCOVFile(options.root / "coverage.info");
}

void
Visualizer::run() {
    using std::chrono::high_resolution_clock;
    using std::chrono::duration_cast;
    using std::chrono::duration;
    using std::chrono::milliseconds;

    auto before = high_resolution_clock::now();

    initSymbolServer();
    walkCoverageFiles();
    cleanupSymbolServer();

    auto after = high_resolution_clock::now();

    auto totalDuration = duration_cast<milliseconds>(after - before);
    printf("INFO: Took %ldms to finish\n", totalDuration.count());
}


