#!/usr/bin/env python3
"""
Plot 2: Run-by-run consistency of GC calls, overhead %, and avg reclaimed,
faceted by configuration (checks run-to-run/independence, per reviewer note).

Input format, one record per line:
    config,run_number,step,elapsed,type,free_before,duration_us,free_after,reclaimed,gc_interval

    gc_interval is the time since the previous collection call, in microseconds (0 for the
    first collection of a run). It is optional: logs without this 10th column still load.
    This script does not plot it, but it is kept in the data frame so the loader matches
    the record layout used by the other scripts.

Usage:
    python plot2_run_consistency.py data.txt
    python plot2_run_consistency.py data.txt --save fig2_run_consistency.png
"""
import argparse

import matplotlib.pyplot as plt
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


def per_run_stats(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cfg in config_order(df):
        d = df[df["config"] == cfg]
        for run in sorted(d["run_number"].unique()):
            r = d[d["run_number"] == run]
            gc = r[r["type"] == "GC"]
            total_elapsed = r["elapsed"].sum()
            rows.append({
                "config": cfg,
                "run": run,
                "gc_calls": len(gc),
                "overhead_pct": 100 * gc["duration_us"].sum() / total_elapsed
                                if total_elapsed else 0.0,
                "avg_reclaimed": gc["reclaimed"].mean() if len(gc) else 0.0,
            })
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("txt_file")
    ap.add_argument("--save", default=None, help="output PNG path")
    args = ap.parse_args()

    df = load(args.txt_file)
    if df.empty:
        raise SystemExit("No valid GC/NR records found.")

    stats = per_run_stats(df)
    all_configs = config_order(df)
    # Configs with zero GC calls in every run (e.g. Disabled) have nothing to
    # draw; leave them out of the bars and mention them in a footnote instead.
    no_gc = [c for c in all_configs if stats[stats["config"] == c]["gc_calls"].sum() == 0]
    configs = [c for c in all_configs if c not in no_gc]
    color = {c: f"C{i}" for i, c in enumerate(all_configs)}   # keep colors consistent with other plots

    fig, axes = plt.subplots(3, 1, figsize=(11, 10), sharex=False, constrained_layout=True)
    metrics = [("gc_calls", "GC Calls", 1),
               ("overhead_pct", "GC Overhead (%)", 1),
               ("avg_reclaimed", "Avg Memory Reclaimed (KB)", 1024)]

    width = 0.15
    runs = sorted(stats["run"].unique())
    offset0 = -(len(configs) - 1) / 2 * width      # center each group on its run tick
    for ax, (col, label, div) in zip(axes, metrics):
        for i, cfg in enumerate(configs):
            sub = stats[stats["config"] == cfg].sort_values("run")
            x = sub["run"].to_numpy() + offset0 + i * width
            ax.bar(x, sub[col] / div, width=width, color=color[cfg], label=cfg)
        ax.set_xticks(runs)
        ax.set_xlim(min(runs) - 0.6, max(runs) + 0.6)
        ax.set_ylabel(label)
        ax.grid(True, axis="y", alpha=0.3)
        ax.set_axisbelow(True)

    # legend above the plots so it never covers bars
    fig.legend(*axes[0].get_legend_handles_labels(), loc="outside upper right",
               ncol=len(configs), fontsize=10, frameon=False)
    fig.suptitle("Run-by-Run Consistency, by Configuration", fontsize=13, x=0.01, ha="left")
    axes[-1].set_xlabel("Run number")
    if no_gc:
        fig.text(0.01, 0.005, f"Not shown (0 GC calls in every run): {', '.join(no_gc)}",
                 fontsize=8, color="gray")

    if args.save:
        fig.savefig(args.save, dpi=150)
        print(f"Wrote {args.save}")
    print(stats.to_string(index=False))
    plt.show()


if __name__ == "__main__":
    main()
