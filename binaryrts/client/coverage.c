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
#include "drmgr.h"
#include "drreg.h"
#include "drx.h"
#include "drsyms.h"
#include "coverage.h"
#include "hashtable.h"
#include "modules.h"
#include "utils.h"
#include <stdint.h>

/*
 * Coverage library for DynamoRIO binary instrumentation client.
 * Partly copied and modified from drcov (DynamoRIO extension).
 * See also:
 * (1) https://dynamorio.org/page_drcov.html
 * (2) https://github.com/DynamoRIO/dynamorio/tree/release_9.0.1/ext/drcovlib
 * (3) https://github.com/DynamoRIO/dynamorio/tree/release_9.0.1/clients/drcov
 */

#ifdef WINDOWS
#include "dr_frontend.h"
#include <winternl.h> /* POBJECT_ATTRIBUTES */
#endif

#ifdef UNIX

#include <syscall.h>
#include <errno.h>
#include <sys/stat.h>

#endif

/* Internal data structures. */

typedef struct _bb_entry_t {
    uint offset;
    uint data; // NOTE: by default, this is the hit count of the BB. If we're dumping BB sizes, this will be the BB size.
} bb_entry_t;

typedef struct _covered_mod_t {
    uint mod_id;
    char *mod_name;
    char *mod_path; /* The path to the module (e.g., path to DLL or EXE file). */
    hashtable_t bb_table;
} covered_mod_t;

typedef struct _coverage_data_t {
    drvector_t covered_modules; /* drvector of covered_mod_t */
} coverage_data_t;

typedef struct _dump_request_t {
    file_t dump_file;
    drvector_t bb_offsets;  /* BBs to dump (with hit count > 0) */
    bool reset;
    bool resolve_symbols;
    char *symbol_path;
    file_t syscalls_dump_file;
} dump_request_t;

typedef struct _bb_entry_iter_data_t {
    bb_entry_t **bb_entry;
    uint offset;
} bb_entry_iter_data_t;

/* Variables for this translation unit. */

static covlib_options_t options;
static char logdir[MAXIMUM_PATH];
static file_t output_file;
static coverage_data_t *global_data;
static int covlib_init_count;
static int dump_count = 0;

/* Syscalls. */

#define INIT_OPENED_FILES 500
#define DEFAULT_SYSCALLS_LOG "coverage.log.syscalls"

static int sysnum_file_open;
#ifdef WINDOWS
static int sysnum_file_create;
#endif
#ifdef UNIX
static int sysnum_file_openat;
#endif
static drvector_t opened_files;

static void
free_opened_file(void *file) {
    dr_global_free(file, MAXIMUM_PATH);
}

#ifdef WINDOWS
/*
 * Lookup syscall number by name on Windows (e.g., "NtOpenFile").
 */
static int
get_sysnum(const char* name)
{
    byte* entry;
    module_data_t* data = dr_lookup_module_by_name("ntdll.dll");
    DR_ASSERT(data != NULL);
    entry = (byte*)dr_get_proc_address(data->handle, name);
    DR_ASSERT(entry != NULL);
    dr_free_module_data(data);
    return drmgr_decode_sysnum_from_wrapper(entry);
}
#endif

/* Dump coverage. */

#define MAX_SYM_RESULT 256

static bool
lookup_symbol(const char *symbol_path, bb_entry_t *bb_entry, OUT char *file, OUT uint64 *line, OUT char *name) {
    drsym_error_t symres;
    drsym_info_t sym;
    sym.struct_size = sizeof(sym);
    sym.name = name;
    sym.name_size = MAX_SYM_RESULT;
    sym.file = file;
    sym.file_size = MAXIMUM_PATH;
    symres = drsym_lookup_address(symbol_path, bb_entry->offset, &sym,
                                  DRSYM_DEFAULT_FLAGS);

    if (symres == DRSYM_SUCCESS) {
        *line = sym.line;
        return true;
    }

    return false;
}

static bool
dump_bb_entry(ptr_uint_t idx, void *entry, void *user_data) {
    bb_entry_t *bb_entry = (bb_entry_t *) entry;
    dump_request_t *request = (dump_request_t *) user_data;

    if (bb_entry->data > 0 || options.dump_bb_size) {
        if (request->resolve_symbols) {
            char file[MAXIMUM_PATH];
            char name[MAX_SYM_RESULT];
            uint64 line;
            if (request->symbol_path && lookup_symbol(request->symbol_path, bb_entry, file, &line, name)) {
                dr_fprintf(request->dump_file,
                           "\t+0x%I64x" NON_FILE_PATH_SEP "%s" NON_FILE_PATH_SEP "%s" NON_FILE_PATH_SEP "%u\n",
                           bb_entry->offset, file, name, line);
            }
        } else if (options.text_dump) {
            dr_fprintf(request->dump_file, "\t+0x%I64x\t%u\n", bb_entry->offset, bb_entry->data);
        } else {
            drvector_append(&request->bb_offsets, (void *) (uintptr_t) bb_entry->offset);
        }
        if (request->reset) {
            bb_entry->data = 0;
        }
    }
    return true;
}

static void
dump_coverage_table(void *drcontext, coverage_data_t *data, dump_request_t *request) {
    ASSERT(data != NULL, "data must not be NULL");

    if (request->resolve_symbols)
        drsym_init(0);

    uint i;
    covered_mod_t *mod_entry;

    for (i = 0; i < data->covered_modules.entries; i++) {
        mod_entry = (covered_mod_t *) drvector_get_entry(&data->covered_modules, i);
        ASSERT(mod_entry != NULL, "failed to get module");
        uint64 entries = mod_entry->bb_table.entries;
        if (entries > 0) {
            dr_fprintf(request->dump_file, "%s" NON_FILE_PATH_SEP "%s\n", mod_entry->mod_name, mod_entry->mod_path);
            if (!options.text_dump) {
                drvector_init(&request->bb_offsets, entries, false, NULL);
            }
            request->symbol_path = mod_entry->mod_path;
            uint j;
            for (j = 0; j < HASHTABLE_SIZE(mod_entry->bb_table.table_bits); j++) {
                hash_entry_t *e = mod_entry->bb_table.table[j];
                while (e != NULL) {
                    hash_entry_t *nexte = e->next;
                    dump_bb_entry(j, e->payload, request);
                    e = nexte;
                }
            }
            if (!options.text_dump) {
                dr_fprintf(request->dump_file, "\tBBs: %d\n", request->bb_offsets.entries);
                dr_write_file(request->dump_file, request->bb_offsets.array,
                              request->bb_offsets.entries * sizeof(void *));
                dr_fprintf(request->dump_file, "\n");
                drvector_delete(&request->bb_offsets);
            }
        }
    }

    if (request->resolve_symbols)
        drsym_exit();
}

static void
dump_coverage_data(void *drcontext, coverage_data_t *data, dump_request_t *request) {
    if (request->dump_file == INVALID_FILE) {
        ASSERT(false, "invalid log file");
        return;
    }
    dump_coverage_table(drcontext, data, request);

    /* We dump opened files into a separate log file, with `.syscalls` suffix. 
     * Resetting the opened files will re-create the vector. 
     */
    if (options.syscalls && request->syscalls_dump_file != INVALID_FILE) {
        char *opened_file;
        for (uint i = 0; i < opened_files.entries; i++) {
            opened_file = (char *) drvector_get_entry(&opened_files, i);
            dr_fprintf(request->syscalls_dump_file, "%s\n", opened_file);
        }
        if (request->reset) {
            drvector_delete(&opened_files);
            drvector_init(&opened_files, INIT_OPENED_FILES, true, free_opened_file);
        }
    }
}

/* Global data management. */

#define INIT_COVERED_BB_ENTRIES 2048

static bool
iter_bb_table(ptr_uint_t idx, void *entry, void *iter_data) {
    bb_entry_iter_data_t *data = (bb_entry_iter_data_t *) iter_data;
    bb_entry_t *bb_entry = (bb_entry_t *) entry;
    if (bb_entry->offset == data->offset) {
        *data->bb_entry = bb_entry;
        return false; /* We stop iteration when we find the right entry. */
    }
    return true;
}

typedef enum {
    NEW_BB, BB_EXISTS, BB_NOT_FOUND
} bb_entry_status_t;

static void
free_bb_entry(void *bb_entry) {
    dr_global_free(bb_entry, sizeof(bb_entry_t));
}

static bb_entry_status_t
add_bb_coverage_entry(void *drcontext, coverage_data_t *data, app_pc start, bb_entry_t **bb_entry) {
    uint mod_id;
    app_pc mod_seg_start;
    char *mod_name;
    char *mod_path;
    covlib_status_t res =
            modtrack_lookup_segment(drcontext, start, &mod_id, &mod_seg_start, &mod_name, &mod_path);
    if (res == COVLIB_SUCCESS) {
        ASSERT(start >= mod_seg_start, "wrong module");
        covered_mod_t *covered_mod_entry = NULL;
        uint offset = (uint) (start - mod_seg_start);

        /* Search for existing coverage module entry. */
        uint i;
        for (i = 0; i < data->covered_modules.entries; i++) {
            covered_mod_entry = drvector_get_entry(&data->covered_modules, i);
            if (covered_mod_entry == NULL)
                break;
            if (covered_mod_entry->mod_id == mod_id)
                break;
            covered_mod_entry = NULL;
        }
        /* If not found, add new coverage module. */
        if (covered_mod_entry == NULL) {
            covered_mod_entry = (covered_mod_t *) dr_global_alloc(sizeof(*covered_mod_entry));
            ASSERT(covered_mod_entry != NULL, "failed to allocate covered module");
            covered_mod_entry->mod_id = mod_id;
            covered_mod_entry->mod_name = mod_name;
            covered_mod_entry->mod_path = mod_path;
            hashtable_init_ex(&covered_mod_entry->bb_table,
                              16U,
                              HASH_INTPTR,
                              false,
                              true,
                              free_bb_entry,
                              NULL,
                              NULL);
            drvector_append(&data->covered_modules, covered_mod_entry);
        } else {
            /* Search for existing BB entry. */
            *bb_entry = hashtable_lookup(&covered_mod_entry->bb_table, (void *) (ptr_uint_t) offset);
            /* If existing BB found, return it right away. */
            if (*bb_entry != NULL) {
                return BB_EXISTS;
            }
        }
        *bb_entry = (bb_entry_t *) dr_global_alloc(sizeof(bb_entry_t));
        (*bb_entry)->offset = offset;
        (*bb_entry)->data = 0;
        hashtable_add(&covered_mod_entry->bb_table, (void *) (ptr_uint_t) offset, (void *) *bb_entry);
        return NEW_BB;
    }
    return BB_NOT_FOUND;
}

static void
destroy_covered_module(void *entry) {
    covered_mod_t *cov_mod_entry = (covered_mod_t *) entry;
    hashtable_delete(&cov_mod_entry->bb_table);
    dr_global_free(cov_mod_entry, sizeof(*cov_mod_entry));
}

#define INIT_COVERED_MOD_ENTRIES 1024
#define DEFAULT_COVERAGE_LOG "coverage.log"

static coverage_data_t *
global_data_create(void) {
    coverage_data_t *data;
    data = dr_global_alloc(sizeof(*data));
    drvector_init(
            &data->covered_modules,
            INIT_COVERED_MOD_ENTRIES,
            true, /* All operations done on the module vector should be synchronized. */
            destroy_covered_module
    );
    return data;
}

static void
global_data_destroy(coverage_data_t *data) {
    drvector_delete(&data->covered_modules);
    dr_close_file(output_file);
    dr_global_free(data, sizeof(*data));
}

/* Event callbacks. */

/*
 * Event handler to filter out syscalls to only include relevant syscalls.
 */
static bool
event_filter_syscall(void *drcontext, int sysnum) {
    return sysnum == sysnum_file_open ||
           #ifdef WINDOWS
           sysnum == sysnum_file_create
           #endif
           #ifdef UNIX
           sysnum == sysnum_file_openat
#endif
            ;
}

/*
 * Syscall hook for opening files.
 */
static bool
event_pre_syscall(void *drcontext, int sysnum) {
    if (
            sysnum == sysnum_file_open ||
            #ifdef WINDOWS
            sysnum == sysnum_file_create
            #endif
            #ifdef UNIX
            sysnum == sysnum_file_openat
#endif
            ) {
        char buf[MAXIMUM_PATH];
        memset(buf, 0, sizeof(buf));
#ifdef WINDOWS
        POBJECT_ATTRIBUTES obj = (POBJECT_ATTRIBUTES)dr_syscall_get_param(drcontext, 2);
        if (obj != NULL) {
            /* convert name from unicode to ansi */
            wchar_t* name = obj->ObjectName->Buffer;
            /* not always null-terminated */
            dr_snprintf(buf,
                MIN(obj->ObjectName->Length / sizeof(obj->ObjectName->Buffer[0]),
                    BUFFER_SIZE_ELEMENTS(buf)),
                "%S", name);
        }
#endif
#ifdef UNIX
        char *filepath_arg;
        if (sysnum == sysnum_file_openat) {
            filepath_arg = (char *) dr_syscall_get_param(drcontext, 1);
        } else if (sysnum == sysnum_file_open) {
            filepath_arg = (char *) dr_syscall_get_param(drcontext, 0);
        }
        dr_snprintf(buf, MAXIMUM_PATH, "%s", filepath_arg);
#endif
        /* We are only interested in actual files (no directories) and
         * ignore accesses to log files which might be generated. */
        if (strstr(buf, ".log") == NULL && strrchr(buf, '.') != NULL) {
            char *file_path = dr_global_alloc(MAXIMUM_PATH);
            memcpy(file_path, buf, MAXIMUM_PATH);
            drvector_append(&opened_files, file_path);
        }
    }
    return true;
}

#define DUMP_LOOKUP_FILE "dump-lookup.log"

/*
* Event handler for DR annotations, which are essentially events emitted by the SUT.
*/
static void
event_annotation(void *data) {
    dump_count += 1;
    char *dump_id = (char *) data;
    // Create dump file containing the coverage information.
    char fname[MAXIMUM_FILENAME];
    dr_snprintf(fname, MAXIMUM_FILENAME, "%d.log", dump_count);
    file_t dump_file = open_file(logdir, fname, DR_FILE_WRITE_OVERWRITE | DR_FILE_ALLOW_LARGE);
    file_t syscalls_dump_file = INVALID_FILE;
    if (options.syscalls) {
        // Create dump file containing the syscalls information.
        char syscalls_fname[MAXIMUM_FILENAME];
        dr_snprintf(syscalls_fname, MAXIMUM_FILENAME, "%d.log.syscalls", dump_count);
        syscalls_dump_file = open_file(logdir, syscalls_fname, DR_FILE_WRITE_OVERWRITE | DR_FILE_ALLOW_LARGE);
    }
    dump_request_t request = {
            .dump_file = dump_file,
            .reset = true,
            .resolve_symbols = options.resolve_symbols,
            .symbol_path = NULL,
            .syscalls_dump_file = syscalls_dump_file
    };
    dump_coverage_data(NULL, global_data, &request);
    dr_close_file(dump_file);
    if (options.syscalls && syscalls_dump_file != INVALID_FILE) {
        dr_close_file(syscalls_dump_file);
    }
    // Create or append to dump lookup file.
    file_t dump_lookup_file = open_file(logdir, DUMP_LOOKUP_FILE, DR_FILE_WRITE_APPEND | DR_FILE_ALLOW_LARGE);
    if (dump_lookup_file == INVALID_FILE) {
        ASSERT(false, "invalid lookup log file");
        return;
    }
    dr_fprintf(dump_lookup_file, "%d;%s\n", dump_count, dump_id);
    dr_close_file(dump_lookup_file);
}

/*
 * A racy increment of the BB's hit counter. This is typically inlined by DynamoRIO clean call optimizer.
 * Notably, this might overflow if hit counts > 2^32 - 1  are encountered.
 */
static void
clean_call(uint *ptr) {
    *ptr += 1;
}

/*
 * Analysis pass for keeping track of BBs that are about to be stored in DR code cache.
 */
static dr_emit_flags_t
event_bb_analysis(void *drcontext, void *tag, instrlist_t *bb,
                  bool for_trace, bool translating, void **user_data) {
    /* do nothing for translation */
    if (translating)
        return DR_EMIT_DEFAULT;

    app_pc start_pc;
    start_pc = dr_fragment_app_pc(tag);
    bb_entry_t *bb_entry = NULL;
    add_bb_coverage_entry(drcontext, global_data, start_pc, &bb_entry);
    if (bb_entry != NULL && !options.dump_bb_size)
        bb_entry->data += 1;
    else if (bb_entry != NULL && options.dump_bb_size) {
        instr_t *end_pc_ins = instrlist_last_app(bb);
        app_pc end_pc = instr_get_app_pc(end_pc_ins);
        bb_entry->data = (uint) (end_pc - start_pc);
    }

    return DR_EMIT_DEFAULT;
}

/*
 * Instrumentation pass for instrumenting instructions that are about to be stored in DR code cache.
 */
static dr_emit_flags_t
event_bb_instrumentation(void *drcontext, void *tag, instrlist_t *bb, instr_t *instr,
                         bool for_trace, bool translating, void *user_data) {
    /* ignore instructions with tool-inserted instrumentation */
    if (!instr_is_app(instr))
        return DR_EMIT_DEFAULT;

    /* BB-level instrumentation: We store the address of the first BB instruction in the global coverage data object. */
    if (!drmgr_is_first_instr(drcontext, instr))
        return DR_EMIT_DEFAULT;

    app_pc start_pc;
    start_pc = dr_fragment_app_pc(tag);

    bb_entry_t *bb_entry = NULL;
    bb_entry_status_t res = add_bb_coverage_entry(drcontext, global_data, start_pc, &bb_entry);

    if (res != BB_NOT_FOUND && bb_entry != NULL) {
#ifdef VERBOSE
        instr_t* ins = NULL;
        NOTIFY(0, "BEFORE instrumentation: \n");
        for (ins = instrlist_first(bb); ins != NULL; ins = instr_get_next(ins)) {
            dr_print_instr(drcontext, STDERR, ins, "");
        }
#endif

#ifdef X86
        /*
         * For runtime dumping, we need to increment the hit count on each execution of the BB.
         * Thus, we prepend every basic block with a hit count increment.
         * 
         * The inc instruction clobbers 5 of the arithmetic eflags,
         * hence, we have to save them around the inc.
         * See https://www.felixcloutier.com/x86/inc#aflags-affected
         * and https://github.com/DynamoRIO/dynamorio/blob/release_9.0.1/api/samples/countcalls.c#L182 for details.
         * We don't need a lock as any hit count > 0 suffices.
         */
        drreg_reserve_aflags(drcontext, bb, instr);
        instrlist_meta_preinsert(bb, instr,
                                 INSTR_CREATE_inc(drcontext, OPND_CREATE_ABSMEM(&(bb_entry->data), OPSZ_4)));
        drreg_unreserve_aflags(drcontext, bb, instr);
#else
        dr_insert_clean_call(drcontext, bb, instr, (void*)clean_call, false, 1, OPND_CREATE_INTPTR(&(bb_entry->data)));
#endif

        /* Just to be sure, we increment the hit count here once in case our racy increment fails. */
        bb_entry->data += 1;

#ifdef VERBOSE
        NOTIFY(0, "AFTER instrumentation: \n");
        for (ins = instrlist_first(bb); ins != NULL; ins = instr_get_next(ins)) {
            dr_print_instr(drcontext, STDERR, ins, "");
        }
#endif
    }

    return DR_EMIT_DEFAULT;
}

covlib_status_t
covlib_exit(void) {
    int count = dr_atomic_add32_return_sum(&covlib_init_count, -1);
    if (count != 0)
        return COVLIB_SUCCESS;

    /* Set up syscalls dump file. */
    file_t syscalls_dump_file = INVALID_FILE;
    if (options.syscalls) {
        if (options.logname) {
            char syscalls_fname[MAXIMUM_FILENAME];
            dr_snprintf(syscalls_fname, MAXIMUM_FILENAME, "%s.syscalls", options.logname);
            syscalls_dump_file = dr_open_file(syscalls_fname, DR_FILE_WRITE_OVERWRITE | DR_FILE_ALLOW_LARGE);
        } else {
            syscalls_dump_file = open_file(logdir, DEFAULT_SYSCALLS_LOG, DR_FILE_WRITE_OVERWRITE | DR_FILE_ALLOW_LARGE);
        }
    }

    /* Dump coverage. */
    dump_request_t request = {
            .dump_file = output_file,
            .reset = false,
            .resolve_symbols = options.resolve_symbols,
            .symbol_path = NULL,
            .syscalls_dump_file = syscalls_dump_file
    };
    dump_coverage_data(NULL, global_data, &request);

    /* Clean up global data and close handle to output file. */
    global_data_destroy(global_data);
    dr_close_file(output_file);

    /* Destroy module table. */
    modtrack_exit();

    /* Clean up syscall-related handles, global data, and event listeners. */
    if (options.syscalls) {
        dr_close_file(syscalls_dump_file);
        drvector_delete(&opened_files);
        dr_unregister_filter_syscall_event(event_filter_syscall);
        drmgr_unregister_pre_syscall_event(event_pre_syscall);
    }

    drmgr_exit();
    drreg_exit();
    drx_exit();

    return COVLIB_SUCCESS;
}

static covlib_status_t
event_init(void) {
    covlib_status_t res;
    uint64 max_elide_jmp = 0;
    uint64 max_elide_call = 0;
    /* assuming no elision */
    if (!dr_get_integer_option("max_elide_jmp", &max_elide_jmp) ||
        !dr_get_integer_option("max_elide_call", &max_elide_call) || max_elide_jmp != 0 ||
        max_elide_call != 0)
        return COVLIB_ERROR_INVALID_SETUP;

    /* create module table */
    res = modtrack_init(&options);
    if (res != COVLIB_SUCCESS)
        return res;

    /* Create global coverage object. */
    global_data = global_data_create();

    /* Init vector for opened files (if tracing syscalls). */
    if (options.syscalls) {
        drvector_init(&opened_files, INIT_OPENED_FILES, true, free_opened_file);
    }

    /* Set up log file. */
    if (options.logname) {
        output_file = dr_open_file(options.logname, DR_FILE_WRITE_OVERWRITE | DR_FILE_ALLOW_LARGE);
    } else {
        output_file = open_file(logdir, DEFAULT_COVERAGE_LOG, DR_FILE_WRITE_OVERWRITE | DR_FILE_ALLOW_LARGE);
    }
    ASSERT(output_file != INVALID_FILE, "invalid logfile");

    return COVLIB_SUCCESS;
}

covlib_status_t
covlib_init(covlib_options_t *ops) {
    int count = dr_atomic_add32_return_sum(&covlib_init_count, 1);
    if (count > 1)
        return COVLIB_SUCCESS;

    if (ops->struct_size != sizeof(options))
        return COVLIB_ERROR_INVALID_PARAMETER;

    options = *ops;
    bool use_default = false;
    if (options.logdir != NULL) {
        /* Try creating logdir. */
#ifdef WINDOWS
        drfront_status_t create_dir_status = drfront_create_dir(options.logdir);
        if (create_dir_status == DRFRONT_SUCCESS || create_dir_status == DRFRONT_ERROR_FILE_EXISTS) {
#endif
#ifdef UNIX
        int ret = mkdir(options.logdir, 0777);
        if (ret == 0 || errno == EEXIST) {
#endif
            dr_snprintf(logdir, BUFFER_SIZE_ELEMENTS(logdir), "%s", options.logdir);
        } else {
            NOTIFY(0, "Could not create output directory at %s, falling back to current directory.\n", options.logdir);
            use_default = true;
        }
    }
    if (options.logdir == NULL || use_default) {
        dr_snprintf(logdir, BUFFER_SIZE_ELEMENTS(logdir), ".");
    }
    NULL_TERMINATE_BUFFER(logdir);
    options.logdir = logdir;

    drmgr_init();
    drx_init();
    drreg_options_t reg_ops = {sizeof(reg_ops), 2 /*max slots needed: aflags*/, false};
    drreg_init(&reg_ops);

    /* Add instrumentation handler (called whenever a new BB is loaded into DR code cache). */
    if (options.runtime_dump) {
        drmgr_register_bb_instrumentation_event(NULL, event_bb_instrumentation, NULL);

        /* Annotations are a means of communication for dumping coverage from the application. */
        dr_annotation_register_call(
                "dynamorio_annotate_log",
                event_annotation,
                false,
                1,
                DR_ANNOTATION_CALL_TYPE_FASTCALL);
    } else {
        drmgr_register_bb_instrumentation_event(event_bb_analysis, NULL, NULL);
    }

    if (options.syscalls) {
#ifdef WINDOWS
        sysnum_file_open = get_sysnum("NtOpenFile");
        sysnum_file_create = get_sysnum("NtCreateFile");
#endif
#ifdef UNIX
        sysnum_file_open = SYS_open;
        sysnum_file_openat = SYS_openat;
#endif
        dr_register_filter_syscall_event(event_filter_syscall);
        drmgr_register_pre_syscall_event(event_pre_syscall);
    }


    return event_init();
}
