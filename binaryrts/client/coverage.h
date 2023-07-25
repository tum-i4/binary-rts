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

#ifndef _CLIENT_COVERAGE_H_
#define _CLIENT_COVERAGE_H_

/*
 * Coverage library for DynamoRIO binary instrumentation client.
 * Partly copied and modified from drcov (DynamoRIO extension).
 * See also:
 * (1) https://dynamorio.org/page_drcov.html
 * (2) https://github.com/DynamoRIO/dynamorio/tree/release_9.0.1/ext/drcovlib
 * (3) https://github.com/DynamoRIO/dynamorio/tree/release_9.0.1/clients/drcov
 */

#ifdef __cplusplus
extern "C" {
#endif

/* Success code for each covlib operation. */
typedef enum {
    COVLIB_SUCCESS,                     /* Operation succeeded. */
    COVLIB_ERROR,                       /* Operation failed. */
    COVLIB_ERROR_INVALID_PARAMETER,     /* Operation failed: invalid parameter */
    COVLIB_ERROR_INVALID_SETUP,         /* Operation failed: invalid DynamoRIO setup */
    COVLIB_ERROR_NOT_FOUND,             /* Operation failed: query not found. */
    COVLIB_ERROR_BUF_TOO_SMALL,         /* Operation failed: buffer too small. */
} covlib_status_t;

/* Specifies the options when initializing covlib. */
typedef struct _covlib_options_t {
    /** Set this to the size of this structure. */
    size_t struct_size;

    /**
     * The DynamoRIO client ID.
     */
    client_id_t client_id;

    /**
     * By default, log files are stored in the current directory. This option
     * overrides that default.
     */
    const char *logdir;

    /**
     * By default, log file names are "coverage.log". This option overrides
     * that default. will be interpreted as file path.
     */
    char *logname;

    /**
     * By default, all modules will be instrumented. This option allows
     * passing a module file, which contains a newline-separated list of modules to instrument.
     */
    char *modules_file;

    /**
     * By default, all covered BBs are dumped when the process exits. This options enables runtime dumping by making use of DynamoRIO's annotation communication means.
     * Note: If runtime dumping is enabled, BBs get instrumented (i.e., modified), since after a dump, the hit counts are reset, but BBs are not reloaded into the code cache.
     */
    bool runtime_dump;

    /**
     * By default, only the start offset of BBs are recorded.
     * This option will cause the BB sizes to be recorded as well, resulting in a slightly different output format
     * (BB_start, BB_size), but only if -text_dump is used.
     * Note: This output format is only compatible with the visualizer project, not with the default BinaryRTS resolver.
     */
    bool dump_bb_size;

    /**
     * By default, covered BB offsets are dumped in binary format. This option enables a less efficient text dump. If symbol resolving is activated, this option gets automatically enabled.
     */
    bool text_dump;

    /**
     * By default, symbols of covered BBs are not resolved. This options enables symbol lookup for file and line information.
     */
    bool resolve_symbols;

    /**
     * By default, no file-related syscalls are traced. This options enables tracing of file-related syscalls and outputs a list of opened files upon coverage dump.
     */
    bool syscalls;
} covlib_options_t;

/* Library interface. */

covlib_status_t
covlib_init(covlib_options_t *ops);

covlib_status_t
covlib_exit(void);

#ifdef __cplusplus
}
#endif

#endif /* _CLIENT_COVERAGE_H_ */
