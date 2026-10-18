#!/usr/bin/env python3
"""
Plot 1: GC pause tail comparison (CCDF) across all configurations.

Input format, one record per line:
    config,run_number,step,elapsed,type,free_before,duration_us,free_after,reclaimed,gc_interval

    gc_interval is the time since the previous collection call, in microseconds (0 for the
    first collection of a run). It is optional: logs without this 10th column still load.
    This script does not plot it, but it is kept in the data frame so the loader matches
    the record layout used by the other scripts.

Usage:
    python plot1_pause_ccdf.py data.txt
    python plot1_pause_ccdf.py data.txt --save fig1_pause_ccdf.png
"""
import argparse

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

COLUMNS = ["config", "run_number", "step", "elapsed", "type",
           "free_before", "duration_us", "free_after", "reclaimed", "gc_interval"]


def load(path: str) -> pd.DataFrame:
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = [p.strip().strip('"') for p in line.strip().split(",")]
            parts = [p for i, p in enumerate(parts) if p or i < 10][:10]
            if len(parts) < 9 or parts[4] not in ("GC", "NR"):
                continue
            try:
                # 10th field (gc_interval) is optional; default to 0 if missing or blank
                gc_interval = int(parts[9]) if len(parts) > 9 and parts[9] else 0
                rows.append([parts[0], int(parts[1]), int(parts[2]), int(parts[3]),
                             parts[4], int(parts[5]), int(parts[6]),
                             int(parts[7]), int(parts[8]), gc_interval])
            except ValueError:
                continue
    return pd.DataFrame(rows, columns=COLUMNS)


def config_order(df):
    seen = []
    for c in df["config"]:
        if c not in seen:
            seen.append(c)
    return seen


def ccdf(values):
    x = np.sort(np.asarray(values, dtype=float))
    n = len(x)
    y = (n - np.arange(n)) / n
    return x, y


def print_percentiles(series: dict) -> None:
    pcts = [50, 95, 99, 99.9]
    print("\nGC pause percentiles (µs)")
    print(f"{'config':<28}{'n':>7}" + "".join(f"{'p'+str(p):>10}" for p in pcts) + f"{'max':>10}")
    for name, vals in series.items():
        v = np.asarray(vals, dtype=float)
        if v.size == 0:
            continue
        row = "".join(f"{np.percentile(v, p):>10.0f}" for p in pcts)
        note = "  (p99.9 unreliable: n<1000)" if v.size < 1000 else ""
        print(f"{name:<28}{v.size:>7}{row}{v.max():>10.0f}{note}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("txt_file")
    ap.add_argument("--save", default=None, help="output PNG path")
    args = ap.parse_args()

    df = load(args.txt_file)
    if df.empty:
        raise SystemExit("No valid GC/NR records found.")

    series = {}
    for cfg in config_order(df):
        gc = df[(df["config"] == cfg) & (df["type"] == "GC")]
        series[cfg] = gc["duration_us"]
    print_percentiles(series)

    # Order legend by median pause (fastest first)
    order = sorted((n for n, v in series.items() if len(v)), key=lambda n: np.median(series[n]))
    colors = {n: f"C{i}" for i, n in enumerate(series)}  # keep original color mapping

    fig, ax = plt.subplots(figsize=(12, 6.5))
    for name in order:
        vals = series[name]
        x, y = ccdf(vals)
        p99 = np.percentile(vals, 99)
        ax.step(x, y, where="post", color=colors[name], lw=1.8,
                label=f"{name}  (n={len(vals)}, p99={p99:.0f} µs, max={np.max(vals):.0f} µs)")
        # mark p99 on each curve
        ax.plot([p99], [0.01], marker="o", ms=6, color=colors[name], mec="white", zorder=5)

    # percentile reference lines
    for yv, lab in [(0.5, "p50"), (0.1, "p90"), (0.01, "p99")]:
        ax.axhline(yv, color="gray", ls="--", lw=0.8, alpha=0.6)
        ax.text(1.002, yv, lab, transform=ax.get_yaxis_transform(),
                va="center", fontsize=9, color="gray")

    ax.set_yscale("log")
    # Label the log y-axis as percentages (100%, 10%, 1%, 0.1%) instead of powers of ten.
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v * 100:g}%"))
    ax.yaxis.set_minor_formatter(mticker.NullFormatter())
    ax.xaxis.set_major_locator(mticker.MultipleLocator(200))
    ax.xaxis.set_minor_locator(mticker.MultipleLocator(50))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_title("GC Pause Tail Comparison (CCDF)", fontsize=14)
    ax.set_xlabel("GC pause duration (µs)", fontsize=11)
    ax.set_ylabel("Share of pauses ≥ x  [log scale]", fontsize=11)
    ax.grid(True, which="major", alpha=0.35)
    ax.grid(True, which="minor", axis="x", alpha=0.12)
    ax.legend(fontsize=10, loc="upper right", title="Sorted by median pause")
    fig.text(0.01, 0.005,
             "Each curve ends at 1/n, so configs with larger n resolve deeper into the tail. "
             "Dots mark p99.", fontsize=8, color="gray")
    fig.tight_layout(rect=(0, 0.02, 1, 1))

    if args.save:
        fig.savefig(args.save, dpi=150)
        print(f"Wrote {args.save}")
    plt.show()


if __name__ == "__main__":
    main()
