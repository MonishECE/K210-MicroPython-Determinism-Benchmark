# K210-MicroPython-Determinism-Benchmark

Evaluating the effects of MicroPython's Garbage Collector (GC) on execution-time determinism using a Yahboom K210 RISC-V microcontroller. 

## Overview
This repository contains all raw data, benchmarking scripts, and benchmarking code for evaluating jitter across the six distinct workloads tested:
1. Bubble Sort
2. Matrix Multiply (8x8)
3. Fibonacci (Iterative)
4. 4-Queens Problem (1st solution)
5. List Updating
6. Dynamic List Creation (Supplemental heap-allocation workload)

---

## Hardware and Firmware Used
- **Microcontroller:** Yahboom K210 Developer Kit (Kendryte K210 64-bit dual-core RISC-V, up to 400 MHz)
- **Firmware**: CanMV MicroPython (v2.0.6, build dated March 17, 2023)
- **IDE:** MaixPy IDE


## Methodology Summary
- **Sample Size:** n = 1000 iterations per trial, repeated across 5 separate trials (5,000 execution samples per GC configuration, 10,000 total per algorithm).
- **Warm-up:** 100 warm-up iterations executed prior to data collection to account for cold-start effects.
- **Control:** Physical board resets performed between trials to ensure identical starting conditions.
- **Timer:** MicroPython's `time.ticks_us()` was used for microsecond-level measurements independent from adjustable system clock values.
- **Statistical Metrics:** Mean, Standard Deviation, Coefficient of Variation (CV), Percentiles (p95, p99), Median Absolute Deviation (MAD) for outlier detection, and Mann-Whitney U tests for distribution comparisons.

---

## Repository Structure
```text

├── scripts/
│   ├── MicroPython benchmarking scripts
│   └── figure/table generation scripts
├── data/
│   └── Raw timing outputs
├── figures/
│   └── Figures and tables from the technical note
└── README.md
```
## Key Findings
- GC configuration produced statistically significant differences in 5/6 workloads.
- Effect sizes were negligible to small (rank-biserial correlation: -0.062 to 0.139).
- Workload characteristics contributed more to execution-time variability than GC configuration.
- Dynamic List Creation produced a `MemoryError` when GC was disabled because the unreachable heap objects could not be reclaimed, causing memory exhaustion.
## Reproducing the Experiment
**Prerequisites:** 
1. Use Yahboom's official setup instructions to install the required software environment for the K210 Developer Kit (link: https://www.yahboom.net/study/K210-Developer-Kit).
2. To successfully run scripts, you must have a USB-C cable that can transfer data.

**How to use repository:**
1. Upload the benchmark scripts in `scripts/` to the K210 using `MaixPy IDE`.
2. Run each benchmark under `GC-enabled` and `GC-disabled` configurations.
3. Export raw timing outputs.
4. Use the analysis scripts to generate statistics and figures.
