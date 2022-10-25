(function(){function r(e,n,t){function o(i,f){if(!n[i]){if(!e[i]){var c="function"==typeof require&&require;if(!f&&c)return c(i,!0);if(u)return u(i,!0);var a=new Error("Cannot find module '"+i+"'");throw a.code="MODULE_NOT_FOUND",a}var p=n[i]={exports:{}};e[i][0].call(p.exports,function(r){var n=e[i][1][r];return o(n||r)},p,p.exports,r,e,n,t)}return n[i].exports}for(var u="function"==typeof require&&require,i=0;i<t.length;i++)o(t[i]);return o}return r})()({1:[function(require,module,exports){
"use strict";
// Globals
let currentModules;
let instrumentedModules;
let moduleFunctionMap;
let enableDebugLogging = false;
const onLoadModule = (moduleName) => {
    console.log(`* New module ${moduleName} loaded.`);
    currentModules.update();
    instrumentCurrentModules();
};
const interceptModuleLoading = () => {
    const kernel32 = Process.findModuleByName('kernel32.dll');
    if (kernel32) {
        const moduleLoadingFunctions = [
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
            }
        ];
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
};
const instrumentCurrentModules = () => {
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
                const interceptor = Interceptor.attach(module.base.add(funcAddr), function (args) {
                    send({ coverage: { [module.name]: [funcAddr] } });
                    interceptor.detach();
                });
            }
            catch (error) {
                console.log(error);
                send({ coverage: { [module.name]: [funcAddr] } });
            }
        }
    }
};
/**
 * Initialize module map and filter to only included modules.
 * @param functionMap
 */
const setupAgent = (functionMap, debug) => {
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
};

},{}]},{},[1])
//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIm5vZGVfbW9kdWxlcy9icm93c2VyLXBhY2svX3ByZWx1ZGUuanMiLCJpbmRleC50cyJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFBQTs7QUNVQSxVQUFVO0FBQ1YsSUFBSSxjQUF5QixDQUFDO0FBQzlCLElBQUksbUJBQWdDLENBQUM7QUFDckMsSUFBSSxpQkFBb0MsQ0FBQztBQUN6QyxJQUFJLGtCQUFrQixHQUFHLEtBQUssQ0FBQztBQUUvQixNQUFNLFlBQVksR0FBaUMsQ0FBQyxVQUFVLEVBQUUsRUFBRTtJQUM5RCxPQUFPLENBQUMsR0FBRyxDQUFDLGdCQUFnQixVQUFVLFVBQVUsQ0FBQyxDQUFDO0lBQ2xELGNBQWMsQ0FBQyxNQUFNLEVBQUUsQ0FBQztJQUN4Qix3QkFBd0IsRUFBRSxDQUFDO0FBQy9CLENBQUMsQ0FBQztBQUVGLE1BQU0sc0JBQXNCLEdBQWUsR0FBRyxFQUFFO0lBQzVDLE1BQU0sUUFBUSxHQUFHLE9BQU8sQ0FBQyxnQkFBZ0IsQ0FBQyxjQUFjLENBQUMsQ0FBQztJQUMxRCxJQUFJLFFBQVEsRUFBRTtRQUNWLE1BQU0sc0JBQXNCLEdBQTRCO1lBQ3BEO2dCQUNJLElBQUksRUFBRSxjQUFjLEVBQUUsUUFBUSxFQUFFO29CQUM1QixPQUFPLENBQUMsSUFBSTt3QkFDUixJQUFJLENBQUMsVUFBVSxHQUFHLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxjQUFjLEVBQUUsQ0FBQztvQkFDL0MsQ0FBQyxFQUFFLE9BQU8sQ0FBQyxHQUFHO3dCQUNWLFlBQVksQ0FBQyxJQUFJLENBQUMsVUFBVSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsVUFBVSxDQUFDLENBQUMsQ0FBQyxTQUFTLENBQUMsQ0FBQztvQkFDaEUsQ0FBQztpQkFDSjthQUNKO1lBQ0Q7Z0JBQ0ksSUFBSSxFQUFFLGNBQWMsRUFBRSxRQUFRLEVBQUU7b0JBQzVCLE9BQU8sQ0FBQyxJQUFJO3dCQUNSLElBQUksQ0FBQyxVQUFVLEdBQUcsSUFBSSxDQUFDLENBQUMsQ0FBQyxD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
