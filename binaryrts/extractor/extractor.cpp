#include "dr_api.h"
#include "drsyms.h"
#include <chrono>
#include <string>

#include "extractor.h"

namespace fs = std::filesystem;

// Keep as macro for convenient usage in format string.
#define NON_FILE_PATH_SEP "\t"
#define TEST(mask, var) (((mask) & (var)) != 0)

void
SourceLineExtractor::initSymbolServer() {
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
SourceLineExtractor::cleanupSymbolServer() {
    if (isInitialized) {
        if (options.debug)
            printf("DEBUG: Done with symbol handler, cleaning up now...\n");
        drsym_exit();
        isInitialized = false;
    }
}

void
SourceLineExtractor::extractSourceLines() {
    using std::chrono::high_resolution_clock;
    using std::chrono::duration_cast;
    using std::chrono::duration;
    using std::chrono::milliseconds;

    auto before = high_resolution_clock::now();

    initSymbolServer();

    drsym_debug_kind_t kind;
    drsym_error_t symres = drsym_get_module_debug_kind(options.file.string().c_str(), &kind);
    bool hasSymbols = false;
    bool hasLines = false;
    printf("INFO: Using symbol format %s\n", TEST(DRSYM_ELF_SYMTAB, kind) ? "ELF symtab" :
                                             (TEST(DRSYM_PECOFF_SYMTAB, kind) ? "PECOFF symtab" :
                                              (TEST(DRSYM_MACHO_SYMTAB, kind) ? "Mach-O symtab" :
                                               (TEST(DRSYM_PDB, kind) ? "PDB" : "no symbols"))));
    if (symres == DRSYM_SUCCESS) {
        hasSymbols = TEST(DRSYM_SYMBOLS, kind);
        hasLines = TEST(DRSYM_LINE_NUMS, kind);
    }
    if (!hasSymbols && !hasLines) {
        printf("ERROR: Could neither find symbol nor line information for binary.\n");
        exit(1);
    }
    printf("INFO: Extracting source lines for all lines.\n");
    OffsetMap sourceLineOffsetMap = extractAllSourceLines();
    SourceLines sourceLines;
    if (options.mode == ExtractorMode::SYMBOLS && hasSymbols) {
        printf("INFO: Filtering source lines to start lines for symbols only.\n");
        sourceLines = filterSourceLinesForSymbols(sourceLineOffsetMap);
    } else {
        for (auto const &lines: sourceLineOffsetMap) {
            sourceLines.emplace_back(lines.second);
        }
    }

    writeSourceLinesToOutput(sourceLines);

    cleanupSymbolServer();

    auto after = high_resolution_clock::now();
    auto totalDuration = duration_cast<milliseconds>(after - before);
    printf("INFO: Took %ld ms to finish\n", totalDuration.count());
}

struct EnumerateLinesCtx {
    OffsetMap *const sourceLineOffsetMap;
    const std::regex *const sourceFileRegex;
};

bool enumerateLinesCb(drsym_line_info_t *info, void *data) {
    auto *enumCtx = static_cast<EnumerateLinesCtx *>(data);
    auto sourceLine = SourceLine{
            "unknown",
            info->file,
            info->line,
            info->line_addr
    };
    if (std::regex_match(sourceLine.file, *enumCtx->sourceFileRegex)) {
        enumCtx->sourceLineOffsetMap->emplace(info->line_addr, sourceLine);
    }
    return true;
}

OffsetMap SourceLineExtractor::extractAllSourceLines() {
    OffsetMap sourceLineOffsetMap{};
    EnumerateLinesCtx ctx{&sourceLineOffsetMap, &sourcePattern};
    drsym_error_t symres = drsym_enumerate_lines(
            options.file.string().c_str(),
            enumerateLinesCb,
            &ctx
    );
    if (symres != DRSYM_SUCCESS) {
        printf("ERROR: Failed to enumerate lines for module %s with error %d\n", options.file.string().c_str(), symres);
    } else {
        printf("INFO: Successfully enumerated lines for module %s\n", options.file.string().c_str());
    }
    return sourceLineOffsetMap;
}

struct EnumerateSymbolsCtx {
    SourceLines *const sourceLines;
    OffsetMap *const sourceLinesOffsetMap;
};

bool enumerateSymbolsCb(const char *name, size_t modoffs, void *data) {
    auto *enumCtx = static_cast<EnumerateSymbolsCtx *>(data);
    auto it = enumCtx->sourceLinesOffsetMap->find(modoffs);
    if (it != enumCtx->sourceLinesOffsetMap->end()) {
        (*it).second.name = name;
        enumCtx->sourceLines->emplace_back((*it).second);
        enumCtx->sourceLinesOffsetMap->erase(it);
    }
    return true;
}

SourceLines SourceLineExtractor::filterSourceLinesForSymbols(OffsetMap &sourceLinesOffsetMap) {
    SourceLines lines{};
    EnumerateSymbolsCtx ctx{&lines, &sourceLinesOffsetMap};
    drsym_error_t symres = drsym_enumerate_symbols(
            options.file.string().c_str(),
            enumerateSymbolsCb,
            &ctx,
            DRSYM_DEFAULT_FLAGS
    );
    if (symres != DRSYM_SUCCESS) {
        printf("ERROR: Failed to enumerate symbols for module %s with error %d\n", options.file.string().c_str(),
               symres);
    } else {
        printf("INFO: Successfully enumerated symbols for module %s\n", options.file.string().c_str());
    }
    return lines;
}

void
SourceLineExtractor::writeSourceLinesToOutput(const SourceLines &sourceLines) {
    fs::path outputFile = options.file.parent_path() / (options.file.filename().string() + ".binaryrts");
    FILE *fp = fopen(outputFile.string().c_str(), "w+");
    for (const auto &sourceLine: sourceLines) {
        fprintf(fp, "0x%zx" NON_FILE_PATH_SEP "%s" NON_FILE_PATH_SEP "%s" NON_FILE_PATH_SEP "%lu\n",
                sourceLine.offset, sourceLine.file.c_str(), sourceLine.name.c_str(),
                sourceLine.line);
    }
    fclose(fp);
}