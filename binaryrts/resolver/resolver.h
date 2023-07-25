#pragma once

#include <string>
#include <filesystem>
#include <vector>
#include <memory>
#include <optional>
#include <regex>
#include <unordered_map>

namespace fs = std::filesystem;

// A covered symbol contains detailed resolved symbol information.
struct CoveredSymbol {

    enum class SymbolStatus {
        UNRESOLVED,
        NOT_FOUND,
        EXCLUDED,
        RESOLVED
    };

    std::string name;
    std::string file;
    uint64_t line;
    size_t offset;
    size_t start;
    size_t end;
    SymbolStatus status;

    [[nodiscard]] inline bool isSameSymbol(size_t otherOffset) const {
        return otherOffset >= start && otherOffset <= end;
    }

    [[nodiscard]] inline bool isSameLine(const CoveredSymbol &other) const {
        return line == other.line && file == other.file;
    }
};

// A symbol cache keeps track of all already resolved symbols across modules and provides a fast lookup cache.
struct SymbolCache {

    // A symbol map keeps track of symbols' offsets and the corresponding resolved symbol information. 
    using SymbolMap = std::unordered_map<uint64_t, std::unique_ptr<CoveredSymbol>>;

    // A module map keeps track of modules (by name) and their corresponding symbols.
    using ModuleMap = std::unordered_map<std::string, SymbolMap>;

    CoveredSymbol *findSymbol(const std::string &moduleName, size_t offset);

    bool hasLoadedModule(const std::string &moduleName) {
        return modules.find(moduleName) != modules.end();
    }

    void loadSymbolsFromDisk(const std::string &moduleName, const fs::path &modulePath);

private:
    ModuleMap modules;
    std::optional<std::pair<std::string, SymbolMap *>> lastQueriedModule;
    std::optional<std::pair<uint64_t, CoveredSymbol *>> lastQueriedSymbol;
};

// A module coverage object is simply a collection of covered symbols (read-only) as returned from the symbol cache.
struct ModuleCoverage {
    std::string moduleName;
    fs::path modulePath;
    std::vector<const CoveredSymbol *> coveredSymbols;

    bool addSymbol(const CoveredSymbol *symbol) {
        bool isSameAsLastSymbol =
                lastSymbol && (lastSymbol->isSameSymbol(symbol->offset) || lastSymbol->isSameLine(*symbol));
        lastSymbol = symbol;
        if (isSameAsLastSymbol) {
            return false;
        }
        for (auto coveredSymbol: coveredSymbols) {
            if (coveredSymbol->isSameSymbol(symbol->offset) || coveredSymbol->isSameLine(*symbol)) {
                return false;
            }
        }
        coveredSymbols.push_back(symbol);
        return true;
    }

private:
    const CoveredSymbol *lastSymbol = nullptr;
};

// A test coverage object aggregates the coverage across all modules for a single test (i.e., a single coverage log file).
using TestCoverage = std::vector<ModuleCoverage>;

// Resolver CLI options.
struct ResolverOptions {
    std::string ext;
    std::string regex;
    fs::path root;
    bool debug;
    bool resolveSymbols;
};

// Symbol resolving orchestration class.
class SymbolResolver {
public:
    explicit SymbolResolver(const ResolverOptions &options) : options{options}, isInitialized{false} {
        if (!options.regex.empty()) {
            regex.emplace(std::regex(options.regex));
        }
    }

    void run();

    const CoveredSymbol *findSymbol(const std::string &moduleName, const fs::path &modulePath, size_t offset);

private:
    void initSymbolServer();

    void cleanupSymbolServer();

    void walkCoverageFiles();

    void analyzeCoverageFile(const fs::path &file);

    static void writeCoverageToFile(const fs::path &file, const TestCoverage &coverage);

    SymbolCache cache;
    const ResolverOptions &options;
    std::optional<std::regex> regex;
    bool isInitialized;
    size_t symbolMatchCounter = 0;
    size_t symbolQueryCounter = 0;
};