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

#ifndef _CLIENT_UTILS_H_
#define _CLIENT_UTILS_H_

#include "dr_api.h"
#include <string.h>


/*
 * Utilities for BinaryRTS DynamoRIO client.
 * Partly copied and modified from drcov (DynamoRIO extension).
 * See also:
 * (1) https://dynamorio.org/page_drcov.html
 * (2) https://github.com/DynamoRIO/dynamorio/tree/release_9.0.1/ext/drcovlib
 * (3) https://github.com/DynamoRIO/dynamorio/tree/release_9.0.1/clients/drcov
 */

extern uint verbose;

/* By default, we expect the user to want debug messages to be printed. */
#define DEBUG

#ifdef DEBUG
#    define ASSERT(x, msg) DR_ASSERT_MSG(x, msg)
#    define NOTIFY(level, fmt, ...)                   \
        do {                                          \
            if (verbose >= (level))                   \
                dr_fprintf(STDERR, fmt, __VA_ARGS__); \
        } while (0)
#else
#    define ASSERT(x, msg)          /* nothing */
#    define NOTIFY(level, fmt, ...) /* nothing */
#endif

/* Macros for buffers. */
#define BUFFER_SIZE_BYTES(buf) sizeof(buf)
#define BUFFER_SIZE_ELEMENTS(buf) (BUFFER_SIZE_BYTES(buf) / sizeof(buf[0]))
#define BUFFER_LAST_ELEMENT(buf) buf[BUFFER_SIZE_ELEMENTS(buf) - 1]
#define NULL_TERMINATE_BUFFER(buf) BUFFER_LAST_ELEMENT(buf) = 0

/* Checks for both debug and release builds: */
#define USAGE_CHECK(x, msg) DR_ASSERT_MSG(x, msg)
#ifndef MIN
#    define MIN(x, y) ((x) <= (y) ? (x) : (y))
#endif

/* check if all bits in mask are set in var */
#define TESTALL(mask, var) (((mask) & (var)) == (mask))
/* check if any bit in mask is set in var */
#define TESTANY(mask, var) (((mask) & (var)) != 0)
/* check if a single bit is set in var */
#define TEST TESTANY

/* Constants. */
#ifdef WINDOWS
#    define DIRSEP '\\'
#else
#    define DIRSEP '/'
#endif

#define NON_FILE_PATH_SEP "\t"  /* Can be used to split strings that may contain filepaths. */

#define MAXIMUM_FILENAME 200

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Opens a file in a given directory with some provided DR flags.
 * The returned handle is platform-agnostic, i.e., a wrapper provided by DR around HANDLE or FILE.
 */
file_t
open_file(const char *dir, const char *fname, uint flags);

/*
 * Utility to move inside a char pointer to the next line.
 * Useful when working with memory maps.
 */
const char *
get_next_line(const char *ptr);

/*
 * Utility to terminate a file path with the null character to get valid C strings, e.g., when parsed from file.
 */
void
null_terminate_path(char *path);

#ifdef __cplusplus
}
#endif

#endif /* _CLIENT_UTILS_H_ */