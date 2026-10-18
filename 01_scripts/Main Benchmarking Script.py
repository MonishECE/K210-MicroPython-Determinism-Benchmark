import gc
import time

# ============================================================
# Physically reset using the reset button on the board
# before each run
# ============================================================
# CONFIGURATION
# ============================================================

WARMUP_ITERATIONS = 35
ITERATIONS = 1000
OBJECTS_PER_ITERATION = 16
ALLOCATION_SIZE = 256
RUNS = 1

THRESHOLD_LEVELS = [
    ("NE",0.10),
    ("High",0.30),
    ("IM",0.60),
    ("Low",0.90)
]

PRINT_STATS = False
PRINT_EVENTS = False
PRINT_EVERY_ITERATION = False

RUN_AUTOMATIC_GC = True
RUN_EXPLICIT_GC = True
RUN_DISABLED = True

# ============================================================
# TIMING
# ============================================================

def ticks_us():
    return time.ticks_us()

def elapsed_us(start):
    return time.ticks_diff(ticks_us(), start)

# ============================================================
# PERCENTILE
# ============================================================

def percentile(values, p):

    if not values:
        return 0

    if len(values) == 1:
        return values[0]

    index = (len(values) - 1) * p

    lower = int(index)
    upper = lower + 1

    if upper >= len(values):
        return values[lower]

    fraction = index - lower

    return int(
        values[lower]
        + (values[upper] - values[lower]) * fraction
    )

# ============================================================
# ALLOCATION WORKLOAD
# ============================================================

def allocation_workload():

    for i in range(OBJECTS_PER_ITERATION):

        x = bytearray(ALLOCATION_SIZE)

        x[0] = i & 0xFF

# x becomes unreachable after the function returns.

# ============================================================
# COMMON STATISTICS
# ============================================================

def print_statistics(label, values):

    if not values:
        print(label, ": no samples")
        return

    total = 0
    minimum = values[0]
    maximum = values[0]

    for value in values:

        total += value

        if value < minimum:
            minimum = value

        if value > maximum:
            maximum = value

    average = total / len(values)

    print()
    print(label)
    print("  samples :", len(values))
    print("  min     :", minimum, "us")
    print("  avg     :", int(average), "us")
    print("  median  :", percentile(values, 0.50), "us")
    print("  p95     :", percentile(values, 0.95), "us")
    print("  p99     :", percentile(values, 0.99), "us")
    print("  p99.9   :", percentile(values, 0.999), "us")
    print("  max     :", maximum, "us")


def print_byte_statistics(label, values):

    if not values:
        print(label, ": no samples")
        return

    total = 0
    minimum = values[0]
    maximum = values[0]

    for value in values:

        total += value

        if value < minimum:
            minimum = value

        if value > maximum:
            maximum = value

    print()
    print(label)
    print("  samples :", len(values))
    print("  min     :", minimum, "bytes")
    print("  avg     :", int(total / len(values)), "bytes")
    print("  median  :", percentile(values, 0.50), "bytes")
    print("  p95     :", percentile(values, 0.95), "bytes")
    print("  p99     :", percentile(values, 0.99), "bytes")
    print("  max     :", maximum, "bytes")


# ============================================================
# DIRECT FIRMWARE GC EVENT ACCESS
# ============================================================

def get_gc_event(index):

    event = gc.auto_event(index)

    return (
        event[0],  # duration_us
        event[1],  # free_before
        event[2],  # free_after
        event[3],  # timestamp_us
    )

def timestamp_in_interval(timestamp, start, end):

    return (
        time.ticks_diff(timestamp, start) >= 0
        and
        time.ticks_diff(end, timestamp) >= 0
    )

# ============================================================
# AUTOMATIC GC FUNCTION
# ============================================================

def run_automatic(run_number):

    # ----------------------------------------------------------------
    # Preallocate all result buffers before the heap baseline is taken
    # ----------------------------------------------------------------
    all_times = [0] * ITERATIONS
    normal_times = [0] * ITERATIONS
    gc_times = [0] * ITERATIONS
    reclaimed_values = [0] * ITERATIONS
    inter_event_intervals = [0] * ITERATIONS
    n_normal = 0
    n_gc = 0
    n_int = 0
    interval = 0

    gc.enable()
#   Set standard threshold value
    gc.threshold(-1)

#   Warm up iterations
    for _ in range(WARMUP_ITERATIONS):
        for _ in range(12):
            allocation_workload()

#   Clear firmware-recorded automatic GC events.
    gc.auto_reset()

#   Start each run from a clean heap.
    gc.collect()
    start_free = gc.mem_free()
    start_alloc = gc.mem_alloc()

    previous_event_timestamp = None

#   Track which firmware events have already been processed.
    processed_events = 0

    for step in range(ITERATIONS):

        # -----------------------------------------------
        # Timed workload interval
        # -----------------------------------------------
        free_before = gc.mem_free()
        start = ticks_us()

        for _ in range(12):
            allocation_workload()

        end = ticks_us()

        elapsed = time.ticks_diff(end, start)

        all_times[step] = elapsed
        had_gc = False

        # -----------------------------------------------
        # Heap measurements after workload
        # -----------------------------------------------

        free_after = gc.mem_free()
        alloc_after = gc.mem_alloc()

        # -----------------------------------------------
        # Read the event records generated by gccollect.c.
        # An event belongs to this benchmark iteration
        # when its firmware timestamp falls between the
        # start and end timestamps of this workload.
        # -----------------------------------------------

        event_count = gc.auto_event_count()

        while processed_events < event_count:

            event_index = processed_events

            event = get_gc_event(event_index)

            duration_us = event[0]
            ev_free_before = event[1]
            ev_free_after = event[2]
            timestamp_us = event[3]

            processed_events += 1

            if timestamp_in_interval(
                timestamp_us,
                start,
                end
            ):

                reclaimed = (
                    ev_free_after
                    - ev_free_before
                )

                gc_times[n_gc] = duration_us
                reclaimed_values[n_gc] = reclaimed
                n_gc += 1
                had_gc = True

                # Interval between firmware GC timestamps

                if previous_event_timestamp is not None:

                    interval = time.ticks_diff(
                        timestamp_us,
                        previous_event_timestamp
                    )

                    inter_event_intervals[n_int] = interval
                    n_int += 1

                previous_event_timestamp = timestamp_us

                #   Print raw data for GC events

                print("Automatic",run_number,step,elapsed,"GC",ev_free_before,duration_us,
                            ev_free_after,reclaimed,interval,sep=',')

                if PRINT_EVENTS:
                    print(
                        "AUTOMATIC GC EVENT",
                        "run=", run_number,
                        "ITER=", step,
                        "GC Call=", event_index,
                        "duration_us=", duration_us,
                        "free_before=", ev_free_before,
                        "free_after=", ev_free_after,
                        "reclaimed=", reclaimed,
                        "timestamp_us=", timestamp_us
                    )

        # -----------------------------------------------
        # Normal iteration
        # -----------------------------------------------
        # An iteration is considered "normal" only when
        # the firmware reported no automatic GC event
        # inside its timed interval.

        if not had_gc:
        #   Print raw data for normal iterations

            print("Automatic",run_number,step,elapsed,"NR",free_before,"0",
                    free_after,"0","0",sep=',')
            normal_times[n_normal] = elapsed
            n_normal += 1

        # -----------------------------------------------
        # Optional per-iteration output
        # -----------------------------------------------

        if PRINT_EVERY_ITERATION:

            print(
                "ITER", step,
                "time=", elapsed,
                "free=", free_after,
                "alloc=", alloc_after
            )

    # -----------------------------------------------
    # Check for events recorded after the final
    # iteration.
    # -----------------------------------------------

    final_event_count = gc.auto_event_count()

    while processed_events < final_event_count:

        event_index = processed_events

        event = get_gc_event(event_index)

        processed_events += 1

        if PRINT_EVENTS:

            print(
                "GC EVENT AFTER WORKLOAD",
                "event=", event_index,
                "duration_us=", event[0],
                "free_before=", event[1],
                "free_after=", event[2],
                "reclaimed=", event[2] - event[1],
                "timestamp_us=", event[3]
            )

    # -----------------------------------------------
    # Explicit final collection
    # -----------------------------------------------

    gc.collect()

    # -----------------------------------------------
    # Firmware event count
    # -----------------------------------------------

    firmware_event_count = gc.auto_event_count()

    firmware_event_overflow = (
        gc.auto_event_overflowed()
    )


    return {

        "run": run_number,

        "start_free": start_free,
        "start_alloc": start_alloc,

        "all_times": all_times,
        "normal_times": normal_times[:n_normal],

        "gc_times": gc_times[:n_gc],

        "reclaimed_values": reclaimed_values[:n_gc],
        "inter_event_intervals": inter_event_intervals[:n_int],

        "firmware_event_count":
            firmware_event_count,

        "firmware_event_overflow":
            firmware_event_overflow,

    }

# ============================================================
# EXPLICIT GC / MANUAL GC FUNCTION
# ============================================================

def run_manual(run_number_m, threshold_label, threshold_fraction):

    # -----------------------------------------------------------------
    # Preallocate all result buffers before the heap baseline is taken.
    # -----------------------------------------------------------------
    all_times = [0] * ITERATIONS
    gc_times = [0] * ITERATIONS
    normal_times = [0] * ITERATIONS
    reclaimed_values = [0] * ITERATIONS
    inter_gc_intervals = [0] * ITERATIONS
    n_gc = 0
    n_normal = 0
    n_int = 0
    inter_gc_interval = 0

    # -----------------------------------------------
    # Clean heap
    # -----------------------------------------------
    gc.enable()
    gc.collect()
    # Warm up iterations
    for _ in range(WARMUP_ITERATIONS):
        for _ in range(12):
            allocation_workload()

    # Disable automatic collection.
    gc.collect()
    gc.disable()

    start_free = gc.mem_free()
    start_alloc = gc.mem_alloc()

    # Threshold is a fraction of the heap available after the buffers exist

    MEMORY_THRESHOLD = int(start_free * threshold_fraction)

    previous_gc_timestamp = None

    for step in range(ITERATIONS):

        free_before_alloc = gc.mem_free()
        alloc_before_alloc = gc.mem_alloc()

        # -----------------------------------------------
        # Allocation / workload
        # -----------------------------------------------

        start = ticks_us()

        for _ in range(12):
            allocation_workload()

        allocation_time = elapsed_us(start)

        free_after_alloc = gc.mem_free()
        alloc_after_alloc = gc.mem_alloc()

        # -----------------------------------------------
        # Check memory threshold
        # -----------------------------------------------

        if gc.mem_free() < MEMORY_THRESHOLD:

            # -------------------------------------------
            # Explicit collection
            # -------------------------------------------

            before_gc = gc.mem_free()
            alloc_before_gc = gc.mem_alloc()
            gc_timestamp = ticks_us()
            gc_start = gc_timestamp

            gc.collect()

            gc_time = elapsed_us(gc_start)

            after_gc = gc.mem_free()
            alloc_after_gc = gc.mem_alloc()

            reclaimed = (
                after_gc
                - before_gc
            )

            # Total iteration time includes GC pause.
            total_time = allocation_time + gc_time

            gc_times[n_gc] = gc_time
            reclaimed_values[n_gc] = reclaimed
            n_gc += 1


            if previous_gc_timestamp is not None:
                # ticks_diff handles ticks_us wraparound
                inter_gc_interval = time.ticks_diff(
                    gc_timestamp, previous_gc_timestamp
                )
                inter_gc_intervals[n_int] = inter_gc_interval
                n_int += 1

            previous_gc_timestamp = gc_timestamp

            if PRINT_EVENTS:

                print(
                    "MANUAL GC",
                    "step=", step,
                    "allocation=", allocation_time, "us",
                    "gc=", gc_time, "us",
                    "total=", total_time, "us",
                    "free_before_alloc=",
                    free_before_alloc,
                    "free_after_alloc=",
                    free_after_alloc,
                    "free_before_gc=",
                    before_gc,
                    "free_after_gc=",
                    after_gc,
                    "reclaimed=",
                    reclaimed,
                    "inter_gc_interval=",
                    inter_gc_interval, "us"
                )
            # Print raw data for GC events

            print(threshold_label,run_number_m,step,total_time,"GC",before_gc,gc_time,
                    after_gc,reclaimed,inter_gc_interval,sep=',')

        else:

            # -------------------------------------------
            # No GC in this iteration
            # -------------------------------------------

            gc_time = 0
            total_time = allocation_time

            normal_times[n_normal] = total_time
            n_normal += 1
        # Print raw data for normal iterations

            print(threshold_label,run_number_m,step,total_time,"NR",free_before_alloc,"0",
                free_after_alloc,"0","0",sep=',')

        # -----------------------------------------------
        # All iteration times
        # -----------------------------------------------

        all_times[step] = total_time

        # -----------------------------------------------
        # Optional per-iteration output
        # -----------------------------------------------

        if PRINT_EVERY_ITERATION:

            print(
                "ITER", step,
                "time=", total_time,
                "us",
                "allocation=", allocation_time,
                "us",
                "gc=", gc_time,
                "us",
                "free=", gc.mem_free(),
                "alloc=", gc.mem_alloc()
            )


    return {
        "run": run_number_m,
        "threshold": threshold_label,

        "start_free":
            start_free,

        "start_alloc":
            start_alloc,

        "all_times":
            all_times,

        "normal_times":
            normal_times[:n_normal],

        "gc_times":
            gc_times[:n_gc],

        "reclaimed_values":
            reclaimed_values[:n_gc],

        "inter_gc_intervals":
            inter_gc_intervals[:n_int],

    }

# ============================================================
# GC DISABLED FUNCTION
# ============================================================

def run_disabled(run_number):

    times = []
    successful = 0
    failed = False

    failure_step = None
    failure_time = None
    failure_free = None
    failure_alloc = None

    # Start clean.
    gc.enable()
    gc.collect()
    # Warm up iterations
    for _ in range(WARMUP_ITERATIONS):
        for _ in range(12):
            allocation_workload()
    gc.collect()
    gc.disable()
    start_free = gc.mem_free()
    start_alloc = gc.mem_alloc()

    for step in range(ITERATIONS):

        free_before_alloc = gc.mem_free()
        start = ticks_us()
        # -----------------------------------------------
        # Allocation / workload
        # -----------------------------------------------
        try:
            for _ in range(12):
                allocation_workload()

            elapsed = elapsed_us(start)
            free_after_alloc = gc.mem_free()

            times.append(elapsed)

            successful += 1
            print("Disabled",run_number,step,elapsed,"NR",free_before_alloc,"0",
                    free_after_alloc,"0","0",sep=',')
        except MemoryError:

            elapsed = elapsed_us(start)

            failure_step = step
            failure_time = elapsed
            failure_free = gc.mem_free()
            failure_alloc = gc.mem_alloc()
            if PRINT_EVENTS:
                print(
                    "MEMORY ERROR",
                    "\n Iteration =", step,
                    "\n Available Memory =", failure_free,
                    "\n Alloc Memory =", failure_alloc
                )

            failed = True

            break

    # -----------------------------------------------
    # Cleanup
    # -----------------------------------------------

    gc.enable()
    gc.collect()

    return {
        "run": run_number,
        "start_free": start_free,
        "start_alloc": start_alloc,

        "times": times,

        "successful": successful,
        "failed": failed,

        "failure_step": failure_step,
        "failure_time": failure_time,
        "failure_free": failure_free,
        "failure_alloc": failure_alloc,

    }


# ============================================================
# Display automatic summary
# ============================================================

def print_automatic_summary(result):

        print(
            " Run | Free Mem | Avg Exec | "
            "p95 Exec | p99 Exec | p99.9 Exec | Avg no gc | p99 no gc | GC OH% | "
            "GC Events | GC Avg | GC p95 | GC p99 | GC p99.9 | GC Max  | "
            "Avg GC Intr | AR Avg | Reclaim Avg "
        )

        print("-" * 192)

        if result["all_times"]:
            all_avg = int ( sum(result["all_times"]) / len(result["all_times"]) )
            all_p95 = percentile(result["all_times"],0.95)
            all_p99 = percentile(result["all_times"],0.99)
            all_p999 = percentile(result["all_times"],0.999)
        else:
            all_avg = 0
            all_p95 = 0
            all_p99 = 0
            all_p999 = 0

        if result["normal_times"]:
            normal_avg = int ( sum(result["normal_times"]) / len(result["normal_times"]) )
            normal_p99 = percentile(result["normal_times"],0.99)
        else:
            normal_avg = 0
            normal_p99 = 0

        if result["gc_times"]:

            event_avg = int ( sum(result["gc_times"]) / len(result["gc_times"]) )

            event_p95 = percentile(result["gc_times"],0.95)
            event_p99 = percentile(result["gc_times"],0.99)
            event_p999 = percentile(result["gc_times"],0.999)

            event_max = max(result["gc_times"])

            gc_overhead = ( sum(result["gc_times"]) / sum(result["all_times"]) ) * 100

        else:

            event_avg = 0
            event_p95 = 0
            event_p99 = 0
            event_p999 = 0
            event_max = 0
            gc_overhead = 0

        if result["reclaimed_values"]:

            reclaim_avg = int (sum(result["reclaimed_values"]) / len(result["reclaimed_values"]) )

        else:

            reclaim_avg = 0

        if result["inter_event_intervals"]:

            interval_avg = int (sum(result["inter_event_intervals"])
                                / len(result["inter_event_intervals"]) )

        else:

            interval_avg = 0

        rates_avg = int ( ((12 * 16 * 256) * 1000 * 1000000 / sum(result["all_times"])) / 1024 )

        print(
            " {:3} | {:8} | {:8} | {:8} | {:8} | {:10} | {:9} | {:9} | {:6.2f} | "
            "{:9} | {:6} | {:6} | {:6} | {:8} | {:7} | {:11} | {:6} | {:11}".format(
                result["run"],
                result["start_free"],
                all_avg,
                all_p95,
                all_p99,
                all_p999,
                normal_avg,
                normal_p99,
                gc_overhead,
                len(result["gc_times"]),
                event_avg,
                event_p95,
                event_p99,
                event_p999,
                event_max,
                interval_avg,
                rates_avg,
                reclaim_avg

            )
        )

        if result["firmware_event_overflow"]:

            print(
                "WARNING: GC EVENT BUFFER OVERFLOW "
                "run",
                result["run"]
            )

# ============================================================
# Display manual summary
# ============================================================

def print_manual_summary(result):

        gc.collect()
        print(
                " Run | Free Mem | Avg Exec | "
                "p95 Exec | p99 Exec | p99.9 Exec | Avg no gc | p99 no gc | GC OH% | "
                "GC Events | GC Avg | GC p95 | GC p99 | GC p99.9 | GC Max  | "
                "Avg GC Intr | AR Avg | Reclaim Avg "
              )

        print("-" * 192)

        if result["all_times"]:
            all_avg = int( sum(result["all_times"]) / len(result["all_times"]) )
            all_p95 = percentile(result["all_times"],0.95)
            all_p99 = percentile(result["all_times"],0.99)
            all_p999 = percentile(result["all_times"],0.999)
        else:
            all_avg = 0
            all_p95 = 0
            all_p99 = 0
            all_p999 = 0

        if result["normal_times"]:
            normal_avg = int ( sum(result["normal_times"]) / len(result["normal_times"]) )
            normal_p99 = percentile(result["normal_times"],0.99)
        else:
            normal_avg = 0
            normal_p99 = 0

        if result["gc_times"]:

            event_avg = int ( sum(result["gc_times"]) / len(result["gc_times"]) )

            event_p95 = percentile(result["gc_times"],0.95)
            event_p99 = percentile(result["gc_times"],0.99)
            event_p999 = percentile(result["gc_times"],0.999)

            event_max = max(result["gc_times"])

            gc_overhead = ( sum(result["gc_times"]) / sum(result["all_times"]) ) * 100

        else:

            event_avg = 0
            event_p95 = 0
            event_p99 = 0
            event_p999 = 0
            event_max = 0
            gc_overhead = 0

        if result["reclaimed_values"]:
            reclaim_avg = int ( sum(result["reclaimed_values"]) / len(result["reclaimed_values"]) )
        else:
            reclaim_avg = 0

        if result["inter_gc_intervals"]:
            intervals_avg = int ( sum(result["inter_gc_intervals"]) / len(result["inter_gc_intervals"]) )
        else:
            intervals_avg = 0
        ratio_avg = int ( ((12 * 16 * 256) * 1000 * 1000000 / sum(result["all_times"])) / 1024 )

        print(
                " {:3} | {:8} | {:8} | {:8} | {:8} | {:10} | {:9} | {:9} | {:6.2f} | "
                "{:9} | {:6} | {:6} | {:6} | {:8} | {:7} | {:11} | {:6} | {:11}".format(
                result["run"],
                result["start_free"],
                all_avg,
                all_p95,
                all_p99,
                all_p999,
                normal_avg,
                normal_p99,
                gc_overhead,
                len(result["gc_times"]),
                event_avg,
                event_p95,
                event_p99,
                event_p999,
                event_max,
                intervals_avg,
                ratio_avg,
                reclaim_avg,

            )
        )
# ============================================================
# Display disabled summary
# ============================================================

def print_disabled_summary(result):
    gc.collect()

    print(
        " Run | Free Mem | Success Itrs | Avg Time |  p99  "
    )

    print("-" * 50)


    if result["times"]:
        all_avg = int( sum(result["times"]) / len(result["times"]) )
        all_p99 = percentile(result["times"],0.99)
    else:
        all_avg = 0
        all_p99 = 0

    print(
            " {:3} | {:8} | {:12} | {:8} | {:5}".format(
                result["run"],
                result["start_free"],
                result["successful"],
                all_avg,
                all_p99,
            )
    )

# ============================================================
# MAIN
# ============================================================

# Start clean
gc.collect()
print()
print("Initial free memory   :", gc.mem_free())
print("Initial allocation    :", gc.mem_alloc())

# ============================================================
# AUTOMATIC GC
# ============================================================
if RUN_AUTOMATIC_GC:
    # Change the run number start value as per the run number
    # Ex: start value should be 5 for run number 5

    for run_number in range(1,RUNS + 1):
        result = run_automatic(run_number)
        result["all_times"].sort()
        result["gc_times"].sort()
        result["normal_times"].sort()
        result["reclaimed_values"].sort()
        result["inter_event_intervals"].sort()

        if PRINT_STATS:
            print()
            print("RUN",run_number,"SUMMARY")
            print(
                  "  Start free          :",
                   result["start_free"]
                  )

            print(
                  "  Start alloc         :",
                   result["start_alloc"]
                  )

            print(
                  "  Firmware GC event count  :",
                   result["firmware_event_count"]
                   )

            print(
                  "  Automatic GC event count :",
                   len(result["gc_times"])
                   )

            print_statistics(
                  "All Times: With and without automatic GC ",
                     result["all_times"]
                    )

            print_statistics(
                      "Iterations without automatic GC",
                     result["normal_times"]
                    )

            print_statistics(
                     "Iterations with automatic GC",
                     result["gc_times"]
                 )

            print_byte_statistics(
                     "Heap reclaimed per automatic GC event",
                        result["reclaimed_values"]
                    )

        print_automatic_summary(result)
        del result
        gc.collect()

# ============================================================
# MANUAL GC WITH HEAP OCCUPANCY
# ============================================================

if RUN_EXPLICIT_GC:

#   LOW HEAP OCCUPANCY - THRESHOLD SET TO 90% OF AVAILABLE HEAP MEMORY
#   INTERMEDIATE (IM)  - THRESHOLD SET TO 60% OF AVAILABLE HEAP MEMORY
#   HIGH HEAP OCCUPANCY - THRESHOLD SET TO 30% OF AVAILABLE HEAP MEMORY
#   NEAR EXHAUSTION (NE) - THRESHOLD SET TO 10% OF AVAILABLE HEAP MEMORY

        for threshold_label, threshold_fraction in THRESHOLD_LEVELS:
        # Change the run number start value as per the run number
        # Ex: start value should be 5 for run number 5

            for run_number_m in range(1,RUNS + 1):
                result_m = run_manual(run_number_m,threshold_label,threshold_fraction)
                result_m["all_times"].sort()
                result_m["gc_times"].sort()
                result_m["normal_times"].sort()
                result_m["reclaimed_values"].sort()
                result_m["inter_gc_intervals"].sort()

                if PRINT_STATS:
                    print()
                    print("RUN",run_number_m,"SUMMARY")

                    print("  Start free :", result_m["start_free"])
                    print("  Start alloc:", result_m["start_alloc"])

                    print(
                             "  Manual GC event count :",
                            len(result_m["gc_times"])
                         )
                    print_statistics(
                         "All times",
                        result_m["all_times"]
                         )

                    print_statistics(
                        "Manual / Explicit GC time",
                        result_m["gc_times"]
                        )

                    print_statistics(
                         "Normal time with out manual GC calls",
                         result_m["normal_times"]
                        )

                    print_byte_statistics(
                        "Heap reclaimed per explicit GC",
                        result_m["reclaimed_values"]
                        )
                    print_statistics(
                        "GC Intervals",
                        result_m["inter_gc_intervals"]
                        )

                print_manual_summary(result_m)
                del result_m
                gc.collect()

# ============================================================
# GC DISABLED
# ============================================================

if RUN_DISABLED:
    print()
    print("=" * 20)
    print("GC DISABLED SUMMARY")
    print("=" * 20)
    gc.collect()

# Change the run number start value as per the run number
# Ex: start value should be 5 for run number 5

    for run_number_d in range(1,RUNS + 1):
        result_d = run_disabled(run_number_d)
        result_d["times"].sort()

        if PRINT_STATS:
            print_statistics(
                "GC-disabled allocation time",
                result_d["times"]
            )

            print()
            print("Start free       :", result_d["start_free"])
            print("Start alloc      :", result_d["start_alloc"])
            print("Successful Iterations :", result_d["successful"])
            print("Failure Iteration     :", result_d["failure_step"])
            print("Memory failure   :", result_d["failed"])
            print("Failure time     :", result_d["failure_time"], "us")
            print("Failure free     :", result_d["failure_free"])
            print("Failure alloc    :", result_d["failure_alloc"])

        print_disabled_summary(result_d)
        del result_d
        gc.collect()
# ============================================================
# RESTORE NORMAL GC
# ============================================================

gc.enable()
gc.collect()

print()
print("End of the program.")
