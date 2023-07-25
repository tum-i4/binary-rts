#include "dr_api.h"
#include "drsyms.h"
#include <chrono>
#include <string>
#include <filesystem>

#include "resolver.h"

// Keep as macro for convenient usage in format string.
#define NON_FILE_PATH_SEP "\t"

namespace {
    const char *DUMP_LOOKUP_FILE = "dump-lookup.log";
    const char *FINAL_DUMP_FILE = "coverage.log";  // irrelevant coverage file
    const size_t MAX_SYM_RESULT = 256;
    const size_t MAX_LINE_LENGTH = 1024;
}

namespace fs = std::filesystem;

CoveredSymbol *
SymbolCache::findSymbol(const std::string &moduleName, const size_t offset) {
    SymbolMap *symbolMap = nullptr;
    bool isSameAsLastQueriedSymbol = false;

    // Check for last queried module.
    if (lastQueriedModule.has_value() && lastQueriedModule.value().first == moduleName) {
        symbolMap = lastQueriedModule.value().second;
        // Check for last queried symbol.
        if (lastQueriedSymbol.has_value()) {
            if (lastQueriedSymbol.value().first == offset) {
                return lastQueriedSymbol.value().second;
            } else if (lastQueriedSymbol.value().second->isSameSymbol(offset)) {
                // In case we found the same symbol with a different offset, we should add it to the cache, if it doesn't exist.
                isSameAsLastQueriedSymbol = true;
            }
        }
    }

    if (symbolMap == nullptr) {
        symbolMap = &modules[moduleName];
    }

    // Lookup by offset.
    std::unique_ptr<CoveredSymbol> &entry = (*symbolMap)[offset];
    if (entry) {
        return entry.get();
    }
    entry = std::make_unique<CoveredSymbol>();

    CoveredSymbol *symbol = entry.get();
    symbol->offset = offset;

    if (isSameAsLastQueriedSymbol) {
        CoveredSymbol *lastSymbol = lastQueriedSymbol.value().second;
        symbol->start = lastSymbol->start;
        symbol->end = lastSymbol->end;
        symbol->name = lastSymbol->name;
        symbol->file = lastSymbol->file;
        symbol->line = lastSymbol->line;
        symbol->status = lastSymbol->status;
    } else {
        symbol->status = CoveredSymbol::SymbolStatus::UNRESOLVED;
        // Update last queried module and symbol.
        lastQueriedModule.emplace(std::make_pair(moduleName, symbolMap));
        lastQueriedSymbol.emplace(std::make_pair(offset, symbol));
    }

    return symbol;
}

void
SymbolCache::loadSymbolsFromDisk(const std::string &moduleName, const fs::path &modulePath) {
    // This will create an empty map for the module in any case.
    SymbolMap *symbolMap = &modules[moduleName];
    fs::path symbolsFile = modulePath.parent_path() / (moduleName + ".binaryrts");
    if (!fs::exists(symbolsFile)) {
        printf("ERROR: Could not locate symbols file at %s\n", symbolsFile.string().c_str());
        return;
    }

    // Read symbols line by line from file.
    FILE *fp = fopen(symbolsFile.string().c_str(), "r");
    char buffer[MAX_LINE_LENGTH];
    while (fgets(buffer, MAX_LINE_LENGTH, fp)) {
        size_t offset;
        char file[MAXIMUM_PATH];
        char name[MAX_SYM_RESULT];
        uint64_t line;
        sscanf(buffer,
               "0x%zx" NON_FILE_PATH_SEP "%s" NON_FILE_PATH_SEP "%s" NON_FILE_PATH_SEP "%lu\n",
               &offset,
               file,
               name,
               &line);
        std::unique_ptr<CoveredSymbol> &entry = (*symbolMap)[offset];
        if (!entry) {
            entry = std::make_unique<CoveredSymbol>();
            entry->offset = offset;
            entry->file = std::string(file);
            entry->line = line;
            entry->start = offset;
            entry->end = offset;
            entry->name = std::string(name);
            entry->status = CoveredSymbol::SymbolStatus::RESOLVED;
        }
    }
    fclose(fp);
}

void
SymbolResolver::initSymbolServer() {
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
SymbolResolver::cleanupSymbolServer() {
    if (isInitialized) {
        if (options.debug)
            printf("DEBUG: Done with symbol handler, cleaning up now...\n");
        drsym_exit();
        isInitialized = false;
    }
}

const CoveredSymbol *
SymbolResolver::findSymbol(const std::string &moduleName, const fs::path &modulePath, const size_t offset) {
    // In case we're not resolving symbols but use pre-extracted symbol information,
    // we need to read them once from disk here.
    if (!options.resolveSymbols && !cache.hasLoadedModule(moduleName)) {
        cache.loadSymbolsFromDisk(moduleName, modulePath);
    }

    CoveredSymbol *symbol = cache.findSymbol(moduleName, offset);

    switch (symbol->status) {
        case CoveredSymbol::SymbolStatus::RESOLVED:
            symbolMatchCounter++;
            return symbol;
        case CoveredSymbol::SymbolStatus::NOT_FOUND:
        case CoveredSymbol::SymbolStatus::EXCLUDED:
            symbolMatchCounter++;
            return nullptr;
        default:
            if (!options.resolveSymbols) {
                if (options.debug) {
                    printf("DEBUG: Symbol not found 0x%zx in %s\n", symbol->offset, modulePath.string().c_str());
                }
                symbol->status = CoveredSymbol::SymbolStatus::NOT_FOUND;
                return nullptr;
            }
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
                    modulePath.string().c_str(),
                    symbol->offset,
                    &sym,
                    DRSYM_DEFAULT_FLAGS
            );
            symbolQueryCounter++;

            if (symres == DRSYM_SUCCESS) {
                symbol->line = sym.line;
                symbol->file = file;
                symbol->name = name;
                symbol->start = sym.start_offs;
                symbol->end = sym.end_offs;
                if (regex.has_value() && !std::regex_match(symbol->file, regex.value())) {
                    symbol->status = CoveredSymbol::SymbolStatus::EXCLUDED;
                } else {
                    symbol->status = CoveredSymbol::SymbolStatus::RESOLVED;
                }
            } else if (symres == DRSYM_ERROR_LOAD_FAILED) {
                if (options.debug)
                    printf("WARN: Load failed for symbol 0x%zx in %s\n", symbol->offset, modulePath.string().c_str());
            } else if (symres == DRSYM_ERROR_SYMBOL_NOT_FOUND) {
                if (options.debug)
                    printf("WARN: Symbol not found 0x%zx in %s\n", symbol->offset, modulePath.string().c_str());
            } else if (symres == DRSYM_ERROR_NOMEM) {
                if (options.debug)
                    printf("WARN: Memory leak when querying symbol 0x%zx in %s\n", symbol->offset,
                           modulePath.string().c_str());
            }
            // In case we didn't find symbols, we still update the status for the cached offset.
            if (symbol->status != CoveredSymbol::SymbolStatus::EXCLUDED &&
                symbol->status != CoveredSymbol::SymbolStatus::RESOLVED) {
                symbol->status = CoveredSymbol::SymbolStatus::NOT_FOUND;
            }
            // We add the start and end offsets to the symbol cache as well.
            cache.findSymbol(moduleName, symbol->start);
            cache.findSymbol(moduleName, symbol->end);
            return symbol->status == CoveredSymbol::SymbolStatus::RESOLVED ? symbol : nullptr;
    }
}

void
SymbolResolver::analyzeCoverageFile(const fs::path &file) {
    if (options.debug)
        printf("DEBUG: Analyzing coverage file %s\n", file.string().c_str());
    // Keep per-file (i.e., per test) vector of covered modules with covered symbols.
    TestCoverage testCoverage;
    ModuleCoverage *currentModule = nullptr;
    bool cursorBelowModuleName = false;
    FILE *fp = fopen(file.string().c_str(), "rb");
    char buffer[MAX_LINE_LENGTH];
    while (fgets(buffer, MAX_LINE_LENGTH, fp)) {
        // There are possible 2 scenarios:
        // binary dump (default):
        // module.exe  C:/path/to/module.exe
        //      BBs: 4174
        //  raw binary data...\n
        // module2.exe ...
        //      ...
        // with -text_dump: 
        // module.exe  C:/path/to/module.exe
        //      +0x52630
        //      ...

        // New module line detected.
        if (buffer[0] != '\t') {
            std::string line{buffer};
            std::size_t pathStartPos = line.find(NON_FILE_PATH_SEP);
            std::size_t lineEndPos = line.find('\n');
            if (pathStartPos != std::string::npos) {
                ModuleCoverage coveredModule;
                coveredModule.modulePath = line.substr(pathStartPos + 1, lineEndPos - pathStartPos - 1);
                coveredModule.moduleName = coveredModule.modulePath.filename().string();
                testCoverage.emplace_back(std::move(coveredModule));
                currentModule = &testCoverage.back();
                cursorBelowModuleName = true;
            }
        }
            // Either we find an offset here (+0x...) or we find the number of (binary) BB offsets (BBs: %d)
        else if (cursorBelowModuleName) {
            if (buffer[0] == '\t' && buffer[1] == '+') {
                std::string line{buffer};
                std::size_t offsetStartPos = line.find('+');
                std::size_t offsetEndPos = line.find(NON_FILE_PATH_SEP, offsetStartPos);
                if (offsetEndPos == std::string::npos) {
                    offsetEndPos = line.find('\n');
                }
                size_t offset = std::strtoul(line.substr(offsetStartPos, offsetEndPos - offsetStartPos).c_str(),
                                             nullptr, 16);
                const CoveredSymbol *symbol = findSymbol(currentModule->moduleName, currentModule->modulePath, offset);
                if (symbol != nullptr) {
                    currentModule->addSymbol(symbol);
                }
            } else {
                int numBBs = 0;
                sscanf(buffer, "\tBBs: %d\n", &numBBs);
                // Prevent reallocation by providing a max. vector capacity.
                currentModule->coveredSymbols.reserve(numBBs);
                for (int i = 0; i < numBBs; i++) {
                    void *offset;
                    // We could also read all bytes at once, but the stdlib (or the OS) should pick a good buffer size 
                    // for I/O read operations that reduces the number of OS context switches.
                    fread(&offset, sizeof(void *), 1, fp);
                    const CoveredSymbol *symbol = findSymbol(currentModule->moduleName, currentModule->modulePath,
                                                             (size_t) offset);
                    if (symbol != nullptr) {
                        currentModule->addSymbol(symbol);
                    }
                }
                // Skip single '\n' after binary BB offsets.
                fread(buffer, 1, 1, fp);
                cursorBelowModuleName = false;
            }

        }
    }

    fclose(fp);

    // Rewrite file by iterating over modules and writing each symbol in a row 
    // such that the result file can be run through the resolver again.
    writeCoverageToFile(file, testCoverage);
}

void
SymbolResolver::writeCoverageToFile(const fs::path &file, const TestCoverage &coverage) {
    FILE *fp = fopen(file.string().c_str(), "wb+");
    for (const auto &coveredModule: coverage) {
        if (!coveredModule.coveredSymbols.empty()) {
            fprintf(fp, "%s" NON_FILE_PATH_SEP "%s\n", coveredModule.moduleName.c_str(),
                    coveredModule.modulePath.string().c_str());
        }
        for (const auto &coveredSymbol: coveredModule.coveredSymbols) {
            fprintf(fp, "\t+0x%zx" NON_FILE_PATH_SEP "%s" NON_FILE_PATH_SEP "%s" NON_FILE_PATH_SEP "%lu\n",
                    coveredSymbol->offset, coveredSymbol->file.c_str(), coveredSymbol->name.c_str(),
                    coveredSymbol->line);
        }
    }
    fclose(fp);
}

void
SymbolResolver::walkCoverageFiles() {
    if (options.debug)
        printf("DEBUG: Searching for coverage files with extension %s in %s\n", options.ext.c_str(),
               options.root.string().c_str());

    for (const auto &path: fs::recursive_directory_iterator(options.root)) {
        if (path.path().extension() == options.ext &&
            path.path().filename() != DUMP_LOOKUP_FILE &&
            path.path().filename() != FINAL_DUMP_FILE) {
            analyzeCoverageFile(path.path());
        }
    }
}

void
SymbolResolver::run() {
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
    if (options.debug)
        printf("DEBUG: Counters at query=%zu, match=%zu\n", symbolQueryCounter, symbolMatchCounter);
}
