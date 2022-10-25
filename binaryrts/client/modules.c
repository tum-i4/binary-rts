/* ***************************************************************************
 * Copyright (c) 2012-2021 Google, Inc.  All rights reserved.
 * ***************************************************************************/

/*
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * * Redistributions of source code must retain the above copyright notice,
 *   this list of conditions and the following disclaimer.
 *
 * * Redistributions in binary form must reproduce the above copyright notice,
 *   this list of conditions and the following disclaimer in the documentation
 *   and/or other materials provided with the distribution.
 *
 * * Neither the name of Google, Inc. nor the names of its contributors may be
 *   used to endorse or promote products derived from this software without
 *   specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL GOOGLE, INC. OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 * LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
 * OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
 * DAMAGE.
 */

#include "dr_api.h"
#include "drvector.h"
#include "drmgr.h"
#include "modules.h"
#include "utils.h"
#include <string.h>

/*
 * Utilities for keeping track of (un)loaded modules in DynamoRIO clients.
 * Partly copied and modified from drcov (DynamoRIO extension).
 * See also:
 * (1) https://dynamorio.org/page_drcov.html
 * (2) https://github.com/DynamoRIO/dynamorio/tree/release_9.0.1/ext/drcovlib
 * (3) https://github.com/DynamoRIO/dynamorio/tree/release_9.0.1/clients/drcov
 */

#define NUM_GLOBAL_MODULE_CACHE 8
#define NUM_THREAD_MODULE_CACHE 4
#define MODULE_TABLE_INIT_SIZE 1024

/* Internal data structures. */
typedef struct _module_entry_t {
    uint id;
    uint containing_id;
    bool unload; /* if the module is unloaded */
    /* The bounds of the segment, or whole module if it's contiguous. */
    app_pc start;
    app_pc end;
    /* A copy of the data.  Segments of non-contiguous modules all share
     * the same data pointer.
     */
    module_data_t *data;
    /* The file offset of the segment */
    uint64 offset;
    app_pc preferred_base;
} module_entry_t;

typedef struct _module_table_t {
    /* A vector of entries.  Non-contiguous modules have entries that
     * are consecutive, with the lowest-address (main entry) first.
     */
    drvector_t vector;
    /* for quick query without lock, assuming pointer-aligned */
    module_entry_t *cache[NUM_GLOBAL_MODULE_CACHE];
} module_table_t;

typedef struct _per_thread_t {
    /* for quick per-thread query without lock */
    module_entry_t *cache[NUM_THREAD_MODULE_CACHE];
} per_thread_t;

/* Variables for this translation unit. */

static covlib_options_t options;
static int modtrack_init_count;
static int tls_idx = -1;
static module_table_t module_table;
static drvector_t instrumented_modules; /* These are the modules that will be instrumented, if they are loaded. */

/* Module data management. */

/* We use direct map cache to avoid locking */
static inline void
global_module_cache_add(module_entry_t **cache, module_entry_t *entry) {
    cache[entry->id % NUM_GLOBAL_MODULE_CACHE] = entry;
}

/* Maintains LRU order in thread-private caches. A new/recent entry is moved to
 * the front, and all other entries are shifted back to make place. For new
 * entries, shifting results in the oldest entry being discarded.
 */
static inline void
thread_module_cache_adjust(module_entry_t **cache, module_entry_t *entry, uint pos,
                           uint max_pos) {
    uint i;
    ASSERT(pos < max_pos, "wrong pos");
    for (i = pos; i > 0; i--)
        cache[i] = cache[i - 1];
    cache[0] = entry;
}

static inline void
thread_module_cache_add(module_entry_t **cache, uint cache_size, module_entry_t *entry) {
    thread_module_cache_adjust(cache, entry, cache_size - 1, cache_size);
}

static void
module_table_entry_free(void *tofree) {
    module_entry_t *entry = (module_entry_t *) tofree;
    if (entry->id == entry->containing_id) /* Else a sub-entry which shares data. */
        dr_free_module_data(((module_entry_t *) entry)->data);
    dr_global_free(entry, sizeof(module_entry_t));
}

static inline bool
pc_is_in_module(module_entry_t *entry, app_pc pc) {
    if (entry != NULL && !entry->unload) {
        if (pc >= entry->start && pc < entry->end)
            return true;
    }
    return false;
}

static inline void
lookup_helper_set_fields(module_entry_t *entry, OUT uint *mod_index, OUT app_pc *seg_base,
                         OUT app_pc *mod_base, OUT char **mod_name, OUT char **mod_path) {
    if (mod_index != NULL)
        *mod_index = entry->id; /* We expose the segment. */
    if (seg_base != NULL)
        *seg_base = entry->start;
    if (mod_base != NULL)
        *mod_base = entry->data->start; /* Yes, absolute base, not segment base. */
    if (mod_name != NULL)
        *mod_name = (char *) dr_module_preferred_name(entry->data);
    if (mod_path != NULL)
        *mod_path = entry->data->full_path;
}

static covlib_status_t
modtrack_lookup_helper(void *drcontext, app_pc pc, OUT uint *mod_index,
                       OUT app_pc *seg_base, OUT app_pc *mod_base, OUT char **mod_name, OUT char **mod_path) {
    per_thread_t *data = (per_thread_t *) drmgr_get_tls_field(drcontext, tls_idx);
    module_entry_t *entry;
    int i;
    /* We assume we never change an entry's data field, even on unload,
     * and thus it is ok to check its value without a lock.
     */
    /* lookup thread module cache */
    for (i = 0; i < NUM_THREAD_MODULE_CACHE; i++) {
        entry = data->cache[i];
        if (pc_is_in_module(entry, pc)) {
            if (i > 0) {
                thread_module_cache_adjust(data->cache, entry, i,
                                           NUM_THREAD_MODULE_CACHE);
            }
            lookup_helper_set_fields(entry, mod_index, seg_base, mod_base, mod_name, mod_path);
            return COVLIB_SUCCESS;
        }
    }
    /* lookup global module cache */
    /* we use a direct map cache, so it is ok to access it without lock */
    for (i = 0; i < NUM_GLOBAL_MODULE_CACHE; i++) {
        entry = module_table.cache[i];
        if (pc_is_in_module(entry, pc)) {
            lookup_helper_set_fields(entry, mod_index, seg_base, mod_base, mod_name, mod_path);
            return COVLIB_SUCCESS;
        }
    }
    /* lookup module table */
    entry = NULL;
    drvector_lock(&module_table.vector);
    for (i = module_table.vector.entries - 1; i >= 0; i--) {
        entry = drvector_get_entry(&module_table.vector, i);
        ASSERT(entry != NULL, "fail to get module entry");
        if (pc_is_in_module(entry, pc)) {
            global_module_cache_add(module_table.cache, entry);
            thread_module_cache_add(data->cache, NUM_THREAD_MODULE_CACHE, entry);
            break;
        }
        entry = NULL;
    }
    if (entry != NULL)
        lookup_helper_set_fields(entry, mod_index, seg_base, mod_base, mod_name, mod_path);
    drvector_unlock(&module_table.vector);
    return entry == NULL ? COVLIB_ERROR_NOT_FOUND : COVLIB_SUCCESS;
}

covlib_status_t
modtrack_lookup_segment(void *drcontext, app_pc pc, OUT uint *segment_index,
                        OUT app_pc *segment_base, OUT char **mod_name, OUT char **mod_path) {
    return modtrack_lookup_helper(drcontext, pc, segment_index, segment_base, NULL, mod_name, mod_path);
}

#define MAX_MODULE_NAME 128

static void
free_instrumented_module(void *tofree) {
    dr_global_free(tofree, MAX_MODULE_NAME);
}

static void
init_instrumented_modules(const char *file) {
    drvector_init(&instrumented_modules, 16, false, free_instrumented_module);
    if (file != NULL) {
        if (instrumented_modules.entries == 0) {
            file_t modules_file = dr_open_file(file, DR_FILE_READ | DR_FILE_ALLOW_LARGE);
            if (modules_file == INVALID_FILE) {
                NOTIFY(0, "Modules file at %s could not be opened, falling back to instrumenting all modules.\n", file);
            } else {
                const char *map, *ptr;
                size_t map_size;
                uint64 file_size;
                if (dr_file_size(modules_file, &file_size)) {
                    map_size = (size_t) file_size;
                    map = (char *) dr_map_file(modules_file, &map_size, 0, NULL, DR_MEMPROT_READ, 0);
                    if (map != NULL && (size_t) file_size <= map_size) {
                        for (ptr = map; ptr < map + file_size;) {
                            char *module_name = dr_global_alloc(MAX_MODULE_NAME);
                            if (dr_sscanf(ptr, "%s\n", module_name) != 1) {
                                // We reached the end, clean up and break.
                                dr_global_free(module_name, MAX_MODULE_NAME);
                                break;
                            }
                            null_terminate_path(module_name);
                            drvector_append(&instrumented_modules, module_name);
                            ptr = get_next_line(ptr);
                        }
                    } else {
                        NOTIFY(0, "Failed to map file %s\n", modules_file);
                    }
                } else {
                    NOTIFY(0, "Failed to get input file size for %s\n", file);
                }
            }
            dr_close_file(modules_file);
        } else {
            NOTIFY(0, "Skipping to parse modules, since modules file was already parsed.\n", 0);
        }
    }
}

/* Event callbacks. */

static void
event_module_unload(void *drcontext, const module_data_t *data) {
    module_entry_t *entry = NULL;
    int i;
    drvector_lock(&module_table.vector);
    for (i = module_table.vector.entries - 1; i >= 0; i--) {
        entry = drvector_get_entry(&module_table.vector, i);
        ASSERT(entry != NULL, "fail to get module entry");
        /* Only check the main (containing) module.
         * This is necessary because the loop is backward.
         */
        if (entry->id == entry->containing_id && pc_is_in_module(entry, data->start))
            break;
        entry = NULL;
    }
    if (entry != NULL) {
        entry->unload = true;
    }
    drvector_unlock(&module_table.vector);
}

static void
event_module_load(void *drcontext, const module_data_t *data, bool loaded) {
    bool instrument_module = false;
    if (instrumented_modules.entries > 0) {
        uint i;
        char *entry;
        const char *module_name = dr_module_preferred_name(data);
        for (i = 0; i < instrumented_modules.entries; i++) {
            entry = drvector_get_entry(&instrumented_modules, i);
            ASSERT(entry != NULL, "failed to get instrumented module entry");
            if (strcmp(entry, module_name) == 0) {
                instrument_module = true;
                break;
            }
        }
        dr_module_set_should_instrument(data->handle, instrument_module);
    }
    if (instrument_module || instrumented_modules.entries == 0) {
        module_entry_t *entry = NULL;
        module_data_t *mod;
        int i;
        /* Some apps repeatedly unload and reload the same module,
         * so we will try to re-use the old one.
         */
        ASSERT(data != NULL, "data must not be NULL");
        drvector_lock(&module_table.vector);
        /* Assuming most recently loaded entries are most likely to be unloaded,
         * we iterate the module table in a backward way for better performance.
         */
        for (i = module_table.vector.entries - 1; i >= 0; i--) {
            entry = drvector_get_entry(&module_table.vector, i);
            mod = entry->data;
            if (entry->unload &&
                /* Only check the main (containing) module.
                 * This is necessary because the loop is backward.
                 */
                entry->id == entry->containing_id &&
                /* If the same module is re-loaded at the same address,
                 * we will try to use the existing entry.
                 */
                mod->start == data->start && mod->end == data->end &&
                mod->entry_point == data->entry_point &&
                #ifdef WINDOWS
                mod->checksum == data->checksum && mod->timestamp == data->timestamp &&
                #endif
                /* If a module w/ no name (there are some) is loaded, we will
                 * keep making new entries.
                 */
                dr_module_preferred_name(data) != NULL &&
                dr_module_preferred_name(mod) != NULL &&
                strcmp(dr_module_preferred_name(data), dr_module_preferred_name(mod)) == 0) {
                entry->unload = false;
                break;
            }
            entry = NULL;
        }
        if (entry == NULL) {
            entry = dr_global_alloc(sizeof(*entry));
            entry->id = module_table.vector.entries;
            entry->containing_id = entry->id;
            entry->start = data->start;
            entry->end = data->end;
            entry->unload = false;
            entry->data = dr_copy_module_data(data);
            drvector_append(&module_table.vector, entry);
            entry->preferred_base = data->preferred_base;
            entry->offset = 0;
        }
        drvector_unlock(&module_table.vector);
        global_module_cache_add(module_table.cache, entry);
    }
}

static void
event_thread_init(void *drcontext) {
    per_thread_t *data = dr_thread_alloc(drcontext, sizeof(*data));
    memset(data->cache, 0, sizeof(data->cache));
    drmgr_set_tls_field(drcontext, tls_idx, data);
}

static void
event_thread_exit(void *drcontext) {
    per_thread_t *data = (per_thread_t *) drmgr_get_tls_field(drcontext, tls_idx);
    ASSERT(data != NULL, "data must not be NULL");
    dr_thread_free(drcontext, data, sizeof(*data));
}

/* Initialization. */

covlib_status_t
modtrack_init(covlib_options_t *ops) {
    options = *ops;
    int count = dr_atomic_add32_return_sum(&modtrack_init_count, 1);
    if (count > 1)
        return COVLIB_SUCCESS;

    if (!drmgr_init() || !drmgr_register_thread_init_event(event_thread_init) ||
        !drmgr_register_thread_exit_event(event_thread_exit) ||
        !drmgr_register_module_load_event(event_module_load) ||
        !drmgr_register_module_unload_event(event_module_unload))
        return COVLIB_ERROR;

    tls_idx = drmgr_register_tls_field();
    if (tls_idx == -1)
        return COVLIB_ERROR;

    init_instrumented_modules(ops->modules_file);
    memset(module_table.cache, 0, sizeof(module_table.cache));
    drvector_init(&module_table.vector, MODULE_TABLE_INIT_SIZE, false, module_table_entry_free);

    return COVLIB_SUCCESS;
}

covlib_status_t
modtrack_exit(void) {
    int count = dr_atomic_add32_return_sum(&modtrack_init_count, -1);
    if (count != 0)
        return COVLIB_SUCCESS;

    drmgr_unregister_tls_field(tls_idx);
    drvector_delete(&module_table.vector);
    drvector_delete(&instrumented_modules);
    drmgr_exit();

    return COVLIB_SUCCESS;
}
