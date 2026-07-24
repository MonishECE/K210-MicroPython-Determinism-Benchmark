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

## Hardware and Firmware used:
Microcontroller: Yahboom K210 Developer Kit (Kendryte K210 64-bit dual-core RISC-V, up to 400 MHz)
Firmware: CanMV MicroPython (v2.0.6, build dated March 17, 2023)
IDE: MaixPy IDE


## Methodology Summary
Sample Size: n = 1000 iterations per trial, repeated across 5 seperate trials (5,000 execution samples per GC configuration, 10,000 total per algorithm).
Warm-up: 100 warm-up iterations executed prior to data collection to account for cold-start effects.
Control: Physical board resets performed between trials to ensure identical starting conditions.
Timer: MicroPython's time.ticks_us() was used for microsecond-level tracking independent from adjustable, system clock values.
Statistical Metrics: Mean, Standard Deviation, Coefficient of Variation (CV), Percentiles (p95, p99), Median Absolute Deviation (MAD) for outlier detection, and Mann-Whitney U tests for distribution comparisons.

---

## Repository Structure
├── scripts/              # MicroPython benchmarking scripts for the K210, and scripts used for figure/table generation
├── data/                 # Raw timing outputs from benchmarking script
├── figures/              # All figures and tables from the technical note
└── README.md
