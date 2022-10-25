// Types
type ModuleLoadingFunction = {
    name: string;
    callback: InvocationListenerCallbacks | InstructionProbeCallback
};

type ModuleFunctionMap = {
    [module: string]: string[];
}

// Globals
let currentModules: ModuleMap;
let instrumentedModules: Set<string>;
let moduleFunctionMap: ModuleFunctionMap;
let enableDebugLogging = false;

const onLoadModule: (moduleName: string) => void = (moduleName) => {
    console.log(`* New module ${moduleName} loaded.`);
    currentModules.update();
    instrumentCurrentModules();
};

const interceptModuleLoading: () => void = () => {
    const kernel32 = Process.findModuleByName('kernel32.dll');
    if (kernel32) {
        const moduleLoadingFunctions: ModuleLoadingFunction[] = [
            {
                name: 'LoadLibraryA', callback: {
                    onEnter(args) {
                        this.moduleName = args[0].readAnsiString();
                    }, onLeave(ret) {
                        onLoadModule(this.moduleName ? this.moduleName : "unknown");
                    }
                }
            },
            {
                name: 'LoadLibraryW', callback: {
                    onEnter(args) {
                        this.moduleName = args[0].readUtf16String();
                    }, onLeave(ret) {
                        onLoadModule(this.moduleName ? this.moduleName : "unknown");
                    }
                }
            },
            {
                name: 'LoadLibraryExA', callback: {
                    onEnter(args) {
                        this.moduleName = args[0].readAnsiString();
                    }, onLeave(ret) {
                        onLoadModule(this.moduleName ? this.moduleName : "unknown");
                    }
                }
            },
            {
                name: 'LoadLibraryExW', callback: {
                    onEnter(args) {
                        this.moduleName = args[0].readUtf16String();
                    }, onLeave(ret) {
                        onLoadModule(this.moduleName ? this.moduleName : "unknown");
                    }
                }
            },
            {
                name: 'LoadPackagedLibrary', callback: {
                    onEnter(args) {
                        this.moduleName = args[0].readUtf16String();
                    }, onLeave(ret) {
                        onLoadModule(this.moduleName ? this.moduleName : "unknown");
                    }
                }
            }];
        const exports = kernel32.enumerateExports();

        for (const symbol of exports) {
            if (symbol.type !== 'function') {
                continue;
            }
            for (const func of moduleLoadingFunctions) {
                if (symbol.name.includes(func.name)) {
                    if (enableDebugLogging) {
                        console.log(`* Instrumenting kernel32.dll:${symbol.name}:${symbol.address}.`);
                    }
                    Interceptor.attach(symbol.address, func.callback);
                }
            }
        }
    }
}

const instrumentCurrentModules: () => void = () => {
    for (const module of currentModules.values()) {
        if (instrumentedModules.has(module.name)) {
            continue;
        }
        instrumentedModules.add(module.name);
        for (const funcAddr of moduleFunctionMap[module.name]) {
            if (enableDebugLogging) {
                console.log(`* Instrumenting ${module.name}!${funcAddr}`);
            }
            try {
                const interceptor = Interceptor.attach(
                    module.base.add(funcAddr),
                    function (args) {
                        send({coverage: {[module.name]: [funcAddr]}});
                        interceptor.detach();
                    });
            } catch (error) {
                console.log(error);
                send({coverage: {[module.name]: [funcAddr]}});
            }
        }
    }
}

/**
 * Initialize module map and filter to only included modules.
 * @param functionMap
 */
const setupAgent: (functionMap: ModuleFunctionMap, debug: boolean) => void = (functionMap, debug) => {
    moduleFunctionMap = functionMap;
    enableDebugLogging = debug;

    // Get all modules from map.
    const modules = Object.keys(functionMap);

    // Instrument all currently loaded modules, if they are in the function map.
    currentModules = new ModuleMap(m => modules.includes(m.name));
    currentModules.update();
    instrumentedModules = new Set();

    if (enableDebugLogging) {
        console.log("================================ Modules in function map ================================");
        console.log(`${modules.map((m) => m + "(" + functionMap[m].length + ")").join("\n")}`);
        console.log("================================ Currently loaded modules ===============================");
        console.log(`${Process.enumerateModules().map(m => [m.name, m.path]).join("\n")}`);
        console.log("================================ Instrumenting current modules ==========================");
    }

    // Instrument current modules.
    instrumentCurrentModules();

    // Enable module load hooking.
    interceptModuleLoading();
};

/**
 * API of frida JS agent.
 */
rpc.exports = {
    setupAgent
}

