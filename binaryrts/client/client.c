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
#include "drx.h"
#include "coverage.h"
#include "utils.h"

/*
 * Coverage library for DynamoRIO binary instrumentation client.
 * Partly copied and modified from drcov (DynamoRIO extension).
 * See also:
 * (1) https://dynamorio.org/page_drcov.html
 * (2) https://github.com/DynamoRIO/dynamorio/tree/release_9.0.1/ext/drcovlib
 * (3) https://github.com/DynamoRIO/dynamorio/tree/release_9.0.1/clients/drcov
 */

/* Data structures. */

enum {
    NUDGE_TERMINATE_PROCESS = 1,
};

/* Global variables. */

uint verbose;

/* Variables for this translation unit. */

static client_id_t client_id;

/* Event callbacks. */

static void
event_nudge(void *drcontext, uint64 argument) {
    NOTIFY(0, "BinaryRTS client received nudge\n", NULL);
    int nudge_arg = (int) argument;
    int exit_arg = (int) (argument >> 32);
    if (nudge_arg == NUDGE_TERMINATE_PROCESS) {
        static int nudge_term_count;
        /* Handle multiple from both NtTerminateProcess and NtTerminateJobObject */
        uint count = dr_atomic_add32_return_sum(&nudge_term_count, 1);
        if (count == 1) {
            dr_exit_process(exit_arg);
        }
    }
    ASSERT(nudge_arg == NUDGE_TERMINATE_PROCESS, "unsupported nudge");
    ASSERT(false, "should not reach");
}

static bool
event_soft_kill(process_id_t pid, int exit_code) {
    NOTIFY(0, "BinaryRTS client received soft kill\n", NULL);
    /* We pass [exit_code, NUDGE_TERMINATE_PROCESS] to target process. */
    dr_config_status_t res;
    res = dr_nudge_client_ex(pid, client_id,
                             NUDGE_TERMINATE_PROCESS | (uint64) exit_code << 32, 0);
    if (res == DR_SUCCESS) {
        /* Skip syscall since target will terminate itself. */
        return true;
    }
    /* else failed b/c target not under DR control or maybe some other
     * error: let syscall go through
     */
    return false;
}

static void
event_exit(void) {
    NOTIFY(0, "BinaryRTS client received exit event\n", NULL);
    covlib_exit();
}

static void
options_init(client_id_t id, int argc, const char *argv[], covlib_options_t *ops) {
    int i;
    const char *token;

    /* default values */
    verbose = 0;
    ops->client_id = id;
    ops->logname = NULL;
    ops->modules_file = NULL;
    ops->text_dump = false;
    ops->resolve_symbols = false;
    ops->runtime_dump = false;
    ops->syscalls = false;

    for (i = 1 /*skip client*/; i < argc; i++) {
        token = argv[i];
        if (strcmp(token, "-logdir") == 0) {
            USAGE_CHECK((i + 1) < argc, "missing logdir path");
            ops->logdir = argv[++i];
        } else if (strcmp(token, "-output") == 0) {
            USAGE_CHECK((i + 1) < argc, "missing output file");
            ops->logname = (char *) argv[++i];
        } else if (strcmp(token, "-text_dump") == 0)
            ops->text_dump = true;
        else if (strcmp(token, "-symbols") == 0) {
            ops->resolve_symbols = true;
            ops->text_dump = true;
        } else if (strcmp(token, "-runtime_dump") == 0)
            ops->runtime_dump = true;
        else if (strcmp(token, "-syscalls") == 0) {
            ops->syscalls = true;
        } else if (strcmp(token, "-modules") == 0) {
            USAGE_CHECK((i + 1) < argc, "missing modules file");
            ops->modules_file = (char *) argv[++i];
        } else if (strcmp(token, "-verbose") == 0) {
            USAGE_CHECK((i + 1) < argc, "missing -verbose number");
            token = argv[++i];
            if (dr_sscanf(token, "%u", &verbose) != 1) {
                USAGE_CHECK(false, "invalid -verbose number");
            }
        } else {
            NOTIFY(0, "UNRECOGNIZED OPTION: \"%s\"\n", token);
            USAGE_CHECK(false, "invalid option");
        }
    }
}

/*
 * Main routine called by DynamoRIO once client is initialized.
 */
DR_EXPORT void
dr_client_main(client_id_t id, int argc, const char *argv[]) {
    covlib_options_t ops = {
            sizeof(ops),
    };
    client_id = id;

    options_init(id, argc, argv, &ops);
    if (covlib_init(&ops) != COVLIB_SUCCESS) {
        NOTIFY(0, "fatal error: covlib failed to initialize\n", NULL);
        dr_abort();
    }

    drx_register_soft_kills(event_soft_kill);
    dr_register_nudge_event(event_nudge, id);
    dr_register_exit_event(event_exit);
}
