#!/usr/bin/env python3
"""
Plot 3: Free-heap sawtooth with the occupancy threshold line, one panel per
configuration. Makes the "higher occupancy label = later trigger" mechanism
visually obvious.

Input format, one record per line:
    config,run_number,step,elapsed,type,free_before,duration_us,free_after,reclaimed,gc_interval

    gc_interval is the time since the previous collection call, in microseconds (0 for the
    first collection of a run). It is optional: logs without this 10th column still load.
    This script does not plot it, but it is kept in the data frame so the loader matches
    the record layout used by the other scripts.

The threshold (free-memory floor) for each manual configuration is computed
as a percentage of --heap-size:
    NE (near-exhaustion): 10% free  -> occupancy 90% at trigger
    High:                 30% free  -> occupancy 70% at trigger
    IM (intermediate):    60% free  -> occupancy 40% at trigger
    Low:                  90% free  -> occupancy 10% at trigger

If --heap-size is not given, it is estimated as the maximum free_before
value observed in the file (a reasonable proxy for total heap capacity).

Usage:
    python plot3_heap_sawtooth.py data.txt --heap-size 697344
    python plot3_heap_sawtooth.py data.txt --run 1 --window 0 200 --save fig3.png
"""
import argparse

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.ticker as mticker
import pandas as pd

COLUMNS = ["config", "run_number", "step", "elapsed", "type",
           "free_before", "duration_us", "free_after", "reclaimed", "gc_interval"]

# ============================================================
# EDIT THIS: total heap size in bytes (the starting free-memory
# value at the beginning of a run). Used to draw the threshold
# lines. Override at runtime with --heap-size instead, if you
# prefer not to edit this file.
# ============================================================
DEFAULT_HEAP_SIZE = 697344   # free bytes available to the app at start of run (= free_after of every manual GC)
# ============================================================

# floor % of heap that must remain free before manual GC triggers
#   NE:   10% free -> occupancy 90% at trigger
#   High: 30% free -> occupancy 70% at trigger
#   IM:   60% free -> occupancy 40% at trigger
#   Low:  90% free -> occupancy 10% at trigger
THRESHOLD_PCT = {
    "NE": 0.10, "NEAR-EXHAUSTION": 0.10, "NEAR EXHAUSTION": 0.10,
    "HIGH": 0.30,
    "IM": 0.60, "INTERMEDIATE": 0.60,
    "LOW": 0.90,
}


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


def threshold_for(config: str, heap_size: float):
    key = config.strip().upper()
    for name, pct in THRESHOLD_PCT.items():
        if name in key:
            return pct * heap_size
    return None  # e.g. "Automatic" has no fixed manual threshold


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("txt_file")
    ap.add_argument("--heap-size", type=float, default=DEFAULT_HEAP_SIZE,
                    help=f"total heap size in bytes (default: {DEFAULT_HEAP_SIZE}, "
                         f"edit DEFAULT_HEAP_SIZE at the top of this file)")
    ap.add_argument("--run", type=int, default=None,
                    help="run to plot for each config (default: first found)")
    ap.add_argument("--window", type=int, nargs=2, metavar=("START", "END"))
    ap.add_argument("--save", default=None, help="output PNG path")
    args = ap.parse_args()

    df = load(args.txt_file)
    if df.empty:
        raise SystemExit("No valid GC/NR records found.")

    heap_size = args.heap_size
    print(f"Using heap size = {heap_size:.0f} bytes")

    configs = config_order(df)
    fig, axes = plt.subplots(len(configs), 1, figsize=(12, 2.0 * len(configs) + 1),
                             sharex=False, constrained_layout=True)
    if len(configs) == 1:
        axes = [axes]

    y_top = df["free_before"].max() / 1024 * 1.05   # shared y-range so swing sizes are comparable

    for ax, cfg in zip(axes, configs):
        d = df[df["config"] == cfg]
        run = args.run if args.run is not None else int(d["run_number"].iloc[0])
        d = d[d["run_number"] == run].sort_values("step")
        if d.empty:
            ax.set_title(f"{cfg}: run {run} not found")
            continue
        gc = d[d["type"] == "GC"]
        thr = threshold_for(cfg, heap_size)

        def draw(a, dd, gg, lw=0.8, ms=20):
            a.plot(dd["step"], dd["free_before"] / 1024, linewidth=lw, color="tab:blue")
            if thr is not None:
                a.axhline(thr / 1024, color="tab:red", linestyle="--", linewidth=1)
            a.scatter(gg["step"], gg["free_before"] / 1024, marker="x", s=ms,
                      color="tab:red", zorder=3, clip_on=False)

        draw(ax, d, gc)
        ax.set_ylim(0, y_top)           # shared across panels
        if args.window:
            ax.set_xlim(*args.window)

        n_points = len(d)
        if n_points <= 30:
            ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
            ax.margins(x=0.03)

        # panel title with GC count; extra context where it helps
        extra = ""
        key = cfg.strip().upper()
        if thr is None and key.startswith("AUTO"):
            extra = "  -  adaptive (no fixed threshold)"
        elif gc.empty:
            extra = f"  -  no GC; heap exhausted at step {int(d['step'].max())}"
        ax.set_title(f"{cfg}  ({len(gc)} GCs){extra}", fontsize=10, loc="left")
        ax.set_ylabel("Free heap (KB)")
        ax.grid(True, alpha=0.3)

        # Zoom inset for dense panels (many cycles merge into a solid block)
        if len(gc) > 300 and not args.window:
            x0 = int(d["step"].min())
            x1 = x0 + 60
            axin = ax.inset_axes([0.55, 0.06, 0.43, 0.50])
            dz = d[(d["step"] >= x0) & (d["step"] <= x1)]
            gz = gc[(gc["step"] >= x0) & (gc["step"] <= x1)]
            draw(axin, dz, gz, lw=1.0, ms=18)
            lo, hi = dz['free_before'].min() / 1024, dz['free_before'].max() / 1024
            axin.set_ylim(lo - 20, max(hi, (thr or 0) / 1024) + 20)   # zoom y too
            axin.set_title(f"zoom: steps {x0}-{x1}", fontsize=7, pad=2)
            axin.tick_params(labelsize=7)
            axin.grid(True, alpha=0.3)
            ax.indicate_inset_zoom(axin, edgecolor="gray")

    axes[-1].set_xlabel("Benchmark iteration (step)")
    handles = [Line2D([], [], color="tab:blue", lw=1, label="Free heap"),
               Line2D([], [], color="tab:red", ls="--", lw=1, label="GC trigger threshold"),
               Line2D([], [], color="tab:red", marker="x", ls="", label="GC event")]
    fig.legend(handles=handles, loc="outside upper right", ncol=3, fontsize=9, frameon=False)
    fig.suptitle("Free Heap vs. Iteration, by Configuration (shared y-axis)", fontsize=13, x=0.01, ha="left")

    if args.save:
        fig.savefig(args.save, dpi=150)
        print(f"Wrote {args.save}")
    plt.show()


if __name__ == "__main__":
    main()
