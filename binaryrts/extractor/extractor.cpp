#include "dr_api.h"
#include "drsyms.h"
#include <chrono>
#include <string>
#include <filesystem>
#include <regex>

#include "extractor.h"

#include "dbghelp.h"
#pragma comment(lib, "dbghelp.lib")

// Keep as macro for convenient usage in format string.
#define NON_FILE_PATH_SEP "\t"

namespace {
    const size_t MAX_SYM_RESULT = 256;
    const size_t MAX_LINE_LENGTH = 512;

    struct EnumSymbolsCbUserContext {
        FunctionDefinitions* functions;
        std::regex* sourcePattern;
        bool debug;
    };

    BOOL
    enumSymbolsCb(
        PSYMBOL_INFO pSymInfo,
        ULONG SymbolSize,
        PVOID UserContext)
    {
        std::string undecoratedName = pSymInfo->Name;
        // Check for function-like symbol tag.
        if (pSymInfo->Tag != 5) {
            return true;
        }

        if (undecoratedName.find("RTTI") != std::string::npos ||
            undecoratedName.find("`vftable") != std::string::npos ||
            undecoratedName.find("__scrt_") != std::string::npos ||
            undecoratedName.find("[thunk]") != std::string::npos ||
            undecoratedName.find("`string'") != std::string::npos ||
            undecoratedName.find("_std_") != std::string::npos ||
            undecoratedName.find("_vcrt_") != std::string::npos ||
            undecoratedName.find("_guard_") != std::string::npos ||
            undecoratedName.find("dtor$") != std::string::npos ||
            undecoratedName.find("__empty_global_delete") != std::string::npos
            ) {
            return true;
        }

        EnumSymbolsCbUserContext* ctx = static_cast<EnumSymbolsCbUserContext*>(UserContext);

        DWORD dwDisplacement;
        IMAGEHLP_LINE64 symbol_line;
        memset(&symbol_line, 0x0, sizeof(symbol_line));
        symbol_line.SizeOfStruct = sizeof(symbol_line);
        if (!SymGetLineFromAddr64(GetCurrentProcess(), pSymInfo->Address, &dwDisplacement, &symbol_line)) {
            return true;
        }

        std::string filename = symbol_line.FileName;
        if (!std::regex_match(filename, *ctx->sourcePattern)) {
            return true;
        }

        if (ctx->debug) {
            printf("0x%llx (flag) %d (tag) for %s at %llx (%s:%d)\n", pSymInfo->Flags, pSymInfo->Tag, pSymInfo->Name, pSymInfo->Address, symbol_line.FileName, symbol_line.LineNumber);
        }
        FunctionDefinition func{
            std::string(pSymInfo->Name),
            filename,
            symbol_line.LineNumber,
            pSymInfo->Address - pSymInfo->ModBase
        };
        ctx->functions->push_back(func);
        return true;
    }
}

namespace fs = std::filesystem;

void
FunctionExtractor::initSymbolServer() {
    if (isInitialized) { return; }

    if (drsym_init(0) != DRSYM_SUCCESS) {
        printf("WARN: Failed to initialize symbol handler\n");
    }
    else {
        if (options.debug)
            printf("DEBUG: Successfully initialized symbol handler\n");
        isInitialized = true;
    }
}

void
FunctionExtractor::cleanupSymbolServer() {
    if (isInitialized) {
        if (options.debug)
            printf("DEBUG: Done with symbol handler, cleaning up now...\n");
        drsym_exit();
        isInitialized = false;
    }
}

void
FunctionExtractor::extractFunctions() {
    using std::chrono::high_resolution_clock;
    using std::chrono::duration_cast;
    using std::chrono::duration;
    using std::chrono::milliseconds;

    auto before = high_resolution_clock::now();

    initSymbolServer();

    FunctionDefinitions functions;
    
    // TODO: implement for Linux systems using drsyms

    DWORD64 dwBaseAddr = 0;
    DWORD64 dwDllBase = SymLoadModuleEx(
        GetCurrentProcess(),                    // target process 
        NULL,                                   // handle to image - not used
        options.file.string().c_str(),                  // name of image file (can be a name that is resolved through the symbol handler path)
        NULL,                                   // name of module - not required
        dwBaseAddr,                             // base address - not required (set to 0 here)
        0,                                      // size of image - not required
        NULL,                                   // MODLOAD_DATA used for special cases 
        0);
    DWORD error;
    if (!dwDllBase) {
        error = GetLastError();
        if (error != ERROR_SUCCESS) {
            printf("ERROR: SymLoadModuleEx returned error: %d\n", error);
            cleanupSymbolServer();
        }
    }
    else {
        printf("Enumerating symbols for module %s with base %llx\n", options.file.string().c_str(), dwDllBase);
        EnumSymbolsCbUserContext ctx{
            &functions,
            &sourcePattern,
            options.debug
        };
        if (!SymEnumSymbols(
            GetCurrentProcess(),
            dwDllBase,
            NULL,
            enumSymbolsCb,
            &ctx
        )) {
            error = GetLastError();
            if (error != ERROR_SUCCESS) {
                printf("ERROR: SymEnumSymbols returned error: %d\n", error);
            }
        }

        writeFunctions(functions);

        cleanupSymbolServer();
    }

    auto after = high_resolution_clock::now();

    auto totalDuration = duration_cast<milliseconds>(after - before);
    printf("INFO: Took %ldms to finish\n", totalDuration.count());
}

void
FunctionExtractor::writeFunctions(const FunctionDefinitions& functions) {
    fs::path outputFile;
    FILE* fp;

    outputFile = options.file.parent_path() / (options.file.filename().string() + ".functions");
    printf("Writing %d functions to file %s\n", functions.size(), outputFile.string().c_str());
    fp = fopen(outputFile.string().c_str(), "w+");
    for (const auto& func : functions) {
        fprintf(fp, "0x%zx\n", func.offset);
    }
    fclose(fp);

    outputFile = options.file.parent_path() / (options.file.filename().string() + ".functions.lookup");
    printf("Storing debug information to to file %s\n", outputFile.string().c_str());
    fp = fopen(outputFile.string().c_str(), "w+");
    for (const auto& func : functions) {
        fprintf(fp, "0x%zx" NON_FILE_PATH_SEP "%s" NON_FILE_PATH_SEP "%s" NON_FILE_PATH_SEP "%lu\n",
            func.offset, func.file.c_str(), func.name.c_str(),
            func.line);
    }
    fclose(fp);
}
