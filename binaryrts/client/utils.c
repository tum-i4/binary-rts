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

#include "utils.h"

/*
 * Utilities for BinaryRTS DynamoRIO client.
 * Partly copied and modified from drcov (DynamoRIO extension).
 * See also:
 * (1) https://dynamorio.org/page_drcov.html
 * (2) https://github.com/DynamoRIO/dynamorio/tree/release_9.0.1/ext/drcovlib
 * (3) https://github.com/DynamoRIO/dynamorio/tree/release_9.0.1/clients/drcov
 */

file_t
open_file(const char *dir, const char *fname, uint flags) {
    char buf[MAXIMUM_PATH];
    file_t f = INVALID_FILE;
    ssize_t len;
    len = dr_snprintf(
            buf, BUFFER_SIZE_ELEMENTS(buf), "%s%c%s", dir, DIRSEP, fname);
    if (len < 0)
        return INVALID_FILE;
    f = dr_open_file(buf, flags);
    if (f != INVALID_FILE)
        return f;
    return INVALID_FILE;
}

const char *
get_next_line(const char *ptr) {
    const char *end = strchr(ptr, '\n');
    if (end == NULL) {
        ptr += strlen(ptr);
    } else {
        for (ptr = end; *ptr == '\n' || *ptr == '\r'; ptr++); /* do nothing */
    }
    return ptr;
}

void
null_terminate_path(char *path) {
    size_t len = strlen(path);
    while (path[len] == '\n' || path[len] == '\r') {
        path[len] = '\0';
        if (len == 0)
            break;
        len--;
    }
}