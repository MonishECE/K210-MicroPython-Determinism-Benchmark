/*
 * This file is part of the MicroPython project, http://micropython.org/
 *
 * Development of the code in this file was sponsored by Microbric Pty Ltd
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2014 Damien P. George
 * Copyright (c) 2017 Pycom Limited
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 THE SOFTWARE.
*/
/*
 * This file is part of the MicroPython project, http://micropython.org/
 *
 * Development of the code in this file was sponsored by Microbric Pty Ltd
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2014 Damien P. George
 * Copyright (c) 2017 Pycom Limited
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

/*
 * This file is part of the MicroPython project, http://micropython.org/
 *
 * Development of the code in this file was sponsored by Microbric Pty Ltd
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2014 Damien P. George
 * Copyright (c) 2017 Pycom Limited
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

#include <stdio.h>

#include "py/mpconfig.h"
#include "py/mpstate.h"
#include "py/gc.h"
#include "py/mpthread.h"
#include "gccollect.h"
#include <sysctl.h>
#include "py/mphal.h"
#include <stdbool.h>
#include <stdint.h>

volatile bool gc_manual_call = false;

uint32_t gc_auto_count = 0;
uint64_t gc_auto_total_time_us = 0;


/*
 * Per-automatic-GC event logging
 *
 * Each event records:
 *   duration_us   = GC pause duration
 *   free_before  = free heap immediately before GC
 *   free_after   = free heap immediately after GC
 *   timestamp_us = timestamp when GC started
 *
 * 2048 events x 16 bytes = 32 KB of static memory.
 */
#define GC_AUTO_EVENT_CAPACITY 2048

typedef struct {
    uint32_t duration_us;
    uint32_t free_before;
    uint32_t free_after;
    uint32_t timestamp_us;
} gc_auto_event_t;

gc_auto_event_t gc_auto_events[GC_AUTO_EVENT_CAPACITY];

uint32_t gc_auto_event_count = 0;
uint32_t gc_auto_event_stored = 0;
bool gc_auto_event_overflow = false;


#define K210_NUM_AREGS 32

static void gc_collect_inner(int level)
{
    // collect on stack
    volatile void* tmp;
    volatile void* sp = &tmp;

    gc_collect_root(
        (void**)sp,
        ((mp_uint_t)MP_STATE_THREAD(stack_top) - (mp_uint_t)sp) / sizeof(void*)
    );

#if MICROPY_PY_THREAD
    // Trace root pointers from other threads
    mp_thread_gc_others();
#endif
}


/*
 * Reset all automatic-GC statistics and event records.
 */
void gc_auto_stats_reset(void)
{
    gc_auto_count = 0;
    gc_auto_total_time_us = 0;

    gc_auto_event_count = 0;
    gc_auto_event_stored = 0;
    gc_auto_event_overflow = false;
}


/*
 * Main garbage collection entry point.
 *
 * Automatic GC:
 *   - records every GC event
 *   - records duration
 *   - records free heap before GC
 *   - records free heap after GC
 *   - records timestamp
 *
 * Manual GC:
 *   - performs collection normally
 *   - does NOT contribute to automatic-GC statistics
 */
void gc_collect(void)
{
    bool is_manual = gc_manual_call;

    gc_info_t info_before;

    /*
     * Measure heap occupancy immediately before automatic GC.
     * This is intentionally outside the timed region so gc_info()
     * does not inflate the measured GC pause.
     */
    if (!is_manual)
    {
        gc_info(&info_before);
    }

    /*
     * Start timing immediately before the actual collection.
     */
    mp_uint_t start_us = mp_hal_ticks_us();

    gc_collect_start();
    gc_collect_inner(0);
    gc_collect_end();

    /*
     * Stop timing immediately after the actual collection.
     */
    mp_uint_t end_us = mp_hal_ticks_us();
    mp_uint_t duration_us = end_us - start_us;


    /*
     * Only automatic collections are recorded.
     */
    if (!is_manual)
    {
        gc_info_t info_after;

        /*
         * Measure heap occupancy immediately after automatic GC.
         */
        gc_info(&info_after);

        /*
         * Preserve the existing aggregate statistics.
         */
        gc_auto_count++;
        gc_auto_total_time_us += duration_us;

        /*
         * Count this GC event.
         */
        gc_auto_event_count++;


        /*
         * Store the individual event if there is room.
         */
        if (gc_auto_event_stored < GC_AUTO_EVENT_CAPACITY)
        {
            gc_auto_events[gc_auto_event_stored].duration_us =
                duration_us;

            gc_auto_events[gc_auto_event_stored].free_before =
                info_before.free;

            gc_auto_events[gc_auto_event_stored].free_after =
                info_after.free;

            gc_auto_events[gc_auto_event_stored].timestamp_us =
                start_us;

            gc_auto_event_stored++;
        }
        else
        {
            /*
             * We still count the event in gc_auto_event_count,
             * but mark that the event buffer could no longer store it.
             */
            gc_auto_event_overflow = true;
        }
    }
}
