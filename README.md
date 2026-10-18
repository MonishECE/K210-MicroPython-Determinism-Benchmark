# K210-MicroPython-Determinism-Benchmark

An experimental study of garbage collection (GC) latency, runtime overhead, and execution-time variability in MicroPython on a Kendryte K210 RISC-V microcontroller.

## Overview

This repository contains the raw experimental data, benchmarking scripts, and supporting figures and tables for the study:

**An Experimental Study of Garbage Collection Latency and Overhead in MicroPython on a K210 RISC-V Platform**

The study investigates how different garbage collection strategies affect execution-time behavior in a resource-constrained embedded environment. Because the standard MicroPython runtime does not expose detailed information about automatically triggered GC events, the firmware was modified to record collection activity, duration, and memory reclamation.

A controlled memory-allocation workload was used to generate repeatable garbage collection pressure. The experiment compares automatic GC, manual GC at four heap-occupancy thresholds, and GC-disabled execution.

---

## Hardware and Firmware

- **Platform:** Kendryte K210 Developer Kit
- **Architecture:** K210 RISC-V dual-core microcontroller
- **Firmware:** Modified MaixPy firmware, `v0.6.2-89-gd8901fd22`
- **Build date:** September 6, 2026
- **Development environment:** MaixPy IDE

The board's total heap was 759,424 bytes. At the beginning of each run, approximately 697 KB of heap remained available after allocating the result buffers.

---

## Experimental Workload

Each workload iteration performs 12 allocation cycles. Each cycle creates 16 consecutive `bytearray` objects of 256 bytes each. The workload therefore requests a total of **49,152 bytes of allocation per iteration**.

The allocated objects are not retained as a collection. Reassigning the local variable and allowing it to go out of scope makes earlier objects unreachable, generating repeated short-lived allocations and garbage collection pressure.

This controlled workload allows the GC configurations to be compared under consistent allocation behavior.

---

## Garbage Collection Configurations

Five experimental configurations were evaluated:

| Configuration | Description |
|---|---|
| **Automatic** | Standard GC behavior, with firmware-level instrumentation to record GC events. |
| **Manual NE** | Automatic GC disabled; manual collection triggered near heap exhaustion (90% heap occupancy). |
| **Manual High** | Automatic GC disabled; Manual collection triggered at 70% heap occupancy. |
| **Manual IM** | Automatic GC disabled; Manual collection triggered at 40% heap occupancy. |
| **Manual Low** | Automatic GC disabled; Manual collection triggered at 10% heap occupancy. |
| **Disabled** | Automatic and explicit garbage collection disabled during the benchmark. |

For manual GC, collection was triggered when free memory fell below the threshold corresponding to the selected heap-occupancy level. The benchmark did not issue explicit `gc.collect()` calls in the Automatic configuration.

---

## Methodology Summary

- **Independent runs:** 5 per configuration.
- **Measured iterations:** 1,000 per run for configurations that completed the workload.
- **Total planned measurements:** 5,000 iterations per configuration.
- **Warm-up:** 35 warm-up iterations, excluded from statistical analysis.
- **Board reset:** The board was physically reset between runs.
- **Idle period:** The board was allowed to idle for 5 minutes after each run to reduce potential thermal drift.
- **Execution-time measurements:** Recorded in microseconds for each iteration.
- **GC event measurements:** Included collection count, duration, free memory before and after collection, memory reclaimed, and inter-collection interval.

### Statistical Analysis

Execution-time statistics were calculated for each run, then summarized across the five independent runs. The analysis included:

- Mean execution time
- Standard deviation
- p95, p99, and p99.9 execution-time percentiles
- GC event counts and collection-duration statistics
- GC overhead
- Free memory before and after collection
- Average memory reclaimed per collection
- Allocation rate

Exact two-sided Mann–Whitney U tests were applied to run-level measurements using five independent observations per configuration. Rank-biserial correlation (RBC) was used to describe effect size, and Holm correction was applied to account for multiple comparisons. Statistical significance was evaluated at `p < 0.05`.

**Statistical unit:** The five independent run-level values per configuration.

---

## Key Findings

### Execution Time and GC Overhead

| Configuration | Mean execution time (µs) | p99 execution time (µs) | Direct GC overhead |
|---|---:|---:|---:|
| Automatic | 3,320 ± 7 | 10,520 ± 149 | 5.22% ± 0.08% |
| Manual NE | 3,055 ± 5 | 9,697 ± 1 | 5.72% ± 0.02% |
| Manual High | 3,486 ± 7 | 9,711 ± 2 | 6.17% ± 0.01% |
| Manual IM | 4,355 ± 4 | 9,698 ± 0 | 6.76% ± 0.01% |
| Manual Low | 8,216 ± 2 | 11,292 ± 1 | 9.52% ± 0.01% |
| Disabled | 2,505 ± 58* | Not comparable | No GC occurred |

*The Disabled configuration completed only 13 iterations before raising `MemoryError`. Its statistics are therefore a limited reference, not a direct comparison with the configurations that completed all 1,000 iterations per run. Values after ± are the standard deviations across run-level results, as reported in the study.*

### Main Observations

- **Automatic GC:** Had the lowest measured direct GC overhead at 5.22%, but showed greater run-to-run variability in p99 execution time.
- **Manual near-exhaustion GC:** Had a slightly higher direct overhead of 5.72%, but a lower and more repeatable p99 execution time for this workload.
- **Earlier manual collection:** Increased collection frequency and total measured GC overhead. Manual Low had 500 collections per run and 9.52% overhead, compared with 79 collections per run and 5.22% overhead for Automatic.
- **Collection duration and memory reclamation:** Earlier collections had shorter pauses but reclaimed less memory per event.
- **Disabled GC:** Could not sustain the workload and failed with `MemoryError` after 13 iterations in every run.
- **Post-collection timing:** Some iterations immediately following a GC event had elevated execution times. The study records this behavior but does not establish its underlying cause.

### Interpreting GC Overhead

GC overhead is defined as the total measured GC duration divided by total elapsed execution time, expressed as a percentage. It represents the **directly measured time spent in garbage collection**; it does not capture every possible indirect effect on execution time, including elevated durations in iterations following a collection.

Consequently, a lower direct GC overhead does not necessarily mean lower mean execution time or lower tail latency.

---

## Repository Structure

```text
K210-MicroPython-Determinism-Benchmark/
├── scripts/
│   └── Benchmarking and analysis scripts
├── data/
│   └── Raw experimental data
├── figures/
│   └── Figures and tables used in the study
└── README.md
```

The descriptions above summarize the intended contents. Refer to the actual files in each directory for the available scripts, datasets, figures, and tables.

---

## Reproducing the Experiment

### Prerequisites

1. A Kendryte K210 Developer Kit.
2. A USB cable that supports data transfer.
3. MaixPy IDE and a compatible K210 development environment.
4. The benchmark scripts and the corresponding modified firmware needed for automatic GC instrumentation.

For hardware setup guidance, see the [Yahboom K210 Developer Kit guide](https://www.yahboom.net/study/K210-Developer-Kit).

### General Procedure

1. Obtain the repository and review the benchmark scripts.
2. Set up the K210 development environment and the firmware version documented in the study.
3. Run the benchmark under the specified GC configuration.
4. Perform the warm-up procedure and reset the board between independent runs as described in the methodology.
5. Save the raw iteration-level measurements and GC event records.
6. Repeat the procedure for each GC configuration.
7. Use the analysis scripts to calculate run-level statistics and reproduce the figures and tables.

**Reproducibility note:** Results may vary with firmware versions, hardware conditions, workload implementation, timer boundaries, and experimental procedures. Automatic GC instrumentation requires the firmware modifications described in the study.

---

## Limitations

- The experiment evaluates one controlled workload with uniform 256-byte allocations and short-lived objects.
- The results are specific to the tested K210 platform, firmware build, and experimental conditions.
- Five independent runs were used per configuration for statistical comparisons.
- The GC-disabled configuration did not complete the full workload, limiting direct comparisons with the other configurations.

The findings should therefore be interpreted as evidence about the evaluated workload and platform, rather than as universal performance characteristics of all MicroPython applications.

---

## Research Context

This project examines the relationship between garbage collection, memory reclamation, and execution-time variability in an embedded MicroPython environment. It provides experimental data for investigating memory-management overhead and timing behavior in resource-constrained and soft real-time applications.
