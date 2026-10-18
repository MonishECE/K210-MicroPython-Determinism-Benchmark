import pandas as pd
import numpy as np
from scipy.stats import mannwhitneyu
from pathlib import Path

# ============================================================
# 1. SETTINGS
# ============================================================

INPUT_FILE = "All_data_run.txt"

CONFIG_ORDER = ["Automatic", "Low", "IM", "High", "NE", "Disabled"]
TEST_CONFIGS = ["Automatic", "Low", "IM", "High", "NE"]
COMPARISONS = [
    ("Automatic", "Low"),
    ("Automatic", "IM"),
    ("Automatic", "High"),
    ("Automatic", "NE"),
]

EXPECTED_RUNS = 5
EXPECTED_ITERATIONS = 1000

COLUMNS = [
    "configuration",
    "run",
    "iteration",
    "elapsed_us",
    "run_type",
    "free_before_mem",
    "gc_duration_us",
    "free_after",
    "reclaimed_bytes",
    "gc_interval",
]

# ============================================================
# 2. LOAD RAW DATA
# ============================================================

if not Path(INPUT_FILE).exists():
    raise FileNotFoundError(
        f"Cannot find {INPUT_FILE}. Put it in the same folder "
        "as this script, or change INPUT_FILE to its full path."
    )

df = pd.read_csv(
    INPUT_FILE,
    header=None,
    names=COLUMNS,
    skipinitialspace=True,
)

# Clean text fields
df["configuration"] = df["configuration"].astype(str).str.strip()
df["run_type"] = df["run_type"].astype(str).str.strip().str.upper()

# Convert numeric columns
NUMERIC_COLUMNS = [
    "run",
    "iteration",
    "elapsed_us",
    "free_before_mem",
    "gc_duration_us",
    "free_after",
    "reclaimed_bytes",
    "gc_interval",
]

for col in NUMERIC_COLUMNS:
    df[col] = pd.to_numeric(df[col], errors="coerce")

if df[["configuration", "run", "iteration", "elapsed_us",
       "gc_duration_us", "run_type"]].isna().any().any():
    raise ValueError(
        "Missing or invalid values detected in essential columns. "
        "Check the raw input file."
    )

# Actual GC duration observations only
df["is_gc_event"] = (
    df["run_type"].eq("GC") &
    df["gc_duration_us"].gt(0)
)

# ============================================================
# 3. VALIDATE COMPLETE RUNS
# ============================================================

print("\n" + "=" * 110)
print("DATA VALIDATION")
print("=" * 110)

validation = (
    df.groupby(["configuration", "run"])
    .agg(
        iterations=("iteration", "size"),
        unique_iterations=("iteration", "nunique"),
    )
    .reset_index()
)

print(validation.to_string(index=False))

for config in TEST_CONFIGS:
    config_data = df[df["configuration"] == config]
    run_counts = config_data.groupby("run")["iteration"].size()

    if len(run_counts) != EXPECTED_RUNS:
        raise ValueError(
            f"{config} has {len(run_counts)} runs; "
            f"expected {EXPECTED_RUNS}."
        )

    if not (run_counts == EXPECTED_ITERATIONS).all():
        raise ValueError(
            f"{config} does not have exactly "
            f"{EXPECTED_ITERATIONS} rows in every run."
        )

print(
    "\nValidation passed: all five tested configurations have "
    "five complete runs of 1,000 iterations."
)

# ============================================================
# 4. CALCULATE RUN-LEVEL SUMMARIES
# ============================================================

run_results = []

for (config, run_id), group in df.groupby(
    ["configuration", "run"], sort=False
):
    # Execution-time metrics use ALL iteration rows,
    # including rows where no GC occurred.
    elapsed = group["elapsed_us"].dropna()

    # GC-duration metrics use actual GC events only.
    gc_durations = group.loc[
        group["is_gc_event"], "gc_duration_us"
    ].dropna()

    total_elapsed = elapsed.sum()
    total_gc_duration = gc_durations.sum()

    gc_overhead = (
        total_gc_duration / total_elapsed * 100
        if total_elapsed > 0
        else np.nan
    )

    run_results.append({
        "configuration": config,
        "run": run_id,
        "n_iterations": len(group),
        "mean_us": elapsed.mean(),
        "p99_us": elapsed.quantile(0.99),
        "mean_gc_duration_us": (
            gc_durations.mean() if len(gc_durations) else np.nan
        ),
        "total_gc_duration_us": total_gc_duration,
        "total_elapsed_us": total_elapsed,
        "gc_overhead_percent": gc_overhead,
        "n_gc_events": int(group["is_gc_event"].sum()),
    })

run_results = pd.DataFrame(run_results)

# Sort configurations in a consistent order
run_results["configuration"] = pd.Categorical(
    run_results["configuration"],
    categories=CONFIG_ORDER,
    ordered=True,
)

run_results = run_results.sort_values(
    ["configuration", "run"]
).reset_index(drop=True)

# ============================================================
# 5. TABLE 1: INDIVIDUAL RUN-LEVEL RESULTS
# ============================================================

print("\n" + "=" * 140)
print("TABLE 1. RUN-LEVEL RESULTS")
print("Times are in microseconds unless otherwise stated.")
print("=" * 140)

table1_columns = [
    "configuration",
    "run",
    "n_iterations",
    "mean_us",
    "p99_us",
    "mean_gc_duration_us",
    "total_gc_duration_us",
    "gc_overhead_percent",
    "n_gc_events",
]

table1 = run_results[table1_columns].copy()

print(table1.round(3).to_string(index=False))

# ============================================================
# 6. TABLE 2: DESCRIPTIVE SUMMARY ACROSS RUNS
# ============================================================

METRICS = [
    "mean_us",
    "p99_us",
    "mean_gc_duration_us",
    "gc_overhead_percent",
]

METRIC_LABELS = {
    "mean_us": "Mean execution time (us)",
    "p99_us": "P99 execution time (us)",
    "mean_gc_duration_us": "Mean GC duration (us)",
    "gc_overhead_percent": "GC overhead (%)",
}

summary_rows = []

for config in CONFIG_ORDER:
    config_runs = run_results[
        run_results["configuration"] == config
    ]

    if config_runs.empty:
        continue

    row = {
        "Configuration": config,
        "Runs": len(config_runs),
        "Iterations per run (range)": (
            f"{int(config_runs['n_iterations'].min())}-"
            f"{int(config_runs['n_iterations'].max())}"
        ),
    }

    for metric in METRICS:
        values = config_runs[metric].dropna()

        mean_value = values.mean() if len(values) else np.nan
        sd_value = (
            values.std(ddof=1) if len(values) > 1 else np.nan
        )

        row[METRIC_LABELS[metric]] = (
            f"{mean_value:.3f} ± {sd_value:.3f}"
            if pd.notna(mean_value) and pd.notna(sd_value)
            else "N/A"
        )

    event_mean = config_runs["n_gc_events"].mean()
    event_sd = (
        config_runs["n_gc_events"].std(ddof=1)
        if len(config_runs) > 1
        else np.nan
    )

    row["GC events per run"] = (
        f"{event_mean:.2f} ± {event_sd:.2f}"
        if pd.notna(event_sd)
        else f"{event_mean:.2f}"
    )

    summary_rows.append(row)

table2 = pd.DataFrame(summary_rows)

print("\n" + "=" * 140)
print("TABLE 2. MEAN ± STANDARD DEVIATION ACROSS RUNS")
print("Each complete run is one independent replicate.")
print("=" * 140)

print(table2.to_string(index=False))

# ============================================================
# 7. HOLM MULTIPLE-COMPARISON CORRECTION
# ============================================================

def holm_adjust(p_values):
    """Return Holm-adjusted p-values in their original order."""
    p_values = np.asarray(p_values, dtype=float)
    m = len(p_values)

    order = np.argsort(p_values)
    sorted_p = p_values[order]

    adjusted_sorted = np.maximum.accumulate(
        (m - np.arange(m)) * sorted_p
    )
    adjusted_sorted = np.minimum(adjusted_sorted, 1.0)

    adjusted = np.empty(m, dtype=float)
    adjusted[order] = adjusted_sorted

    return adjusted


# ============================================================
# 8. TABLE 3: EXACT MANN-WHITNEY U TESTS AND EFFECT SIZES
# ============================================================

test_rows = []

for metric in METRICS:
    metric_results = []

    for first_config, second_config in COMPARISONS:
        first = run_results.loc[
            run_results["configuration"] == first_config, metric
        ].dropna().to_numpy()

        second = run_results.loc[
            run_results["configuration"] == second_config, metric
        ].dropna().to_numpy()

        if len(first) != EXPECTED_RUNS or len(second) != EXPECTED_RUNS:
            raise ValueError(
                f"Unexpected sample size for {metric}: "
                f"{first_config} n={len(first)}, "
                f"{second_config} n={len(second)}."
            )

        # Exact two-sided Mann-Whitney U test.
        # U1 corresponds to the first-named configuration.
        result = mannwhitneyu(
            first,
            second,
            alternative="two-sided",
            method="exact",
        )

        u1 = float(result.statistic)

        # Positive effect size means the first group tends
        # to have larger values than the second group.
        rank_biserial = (
            2 * u1 / (len(first) * len(second))
        ) - 1

        metric_results.append({
            "Metric": METRIC_LABELS[metric],
            "Comparison": f"{first_config} vs {second_config}",
            "n_first": len(first),
            "n_second": len(second),
            "U": u1,
            "p_raw": float(result.pvalue),
            "rank_biserial": rank_biserial,
        })

    # Holm adjustment is performed separately for each metric:
    # four comparisons within each metric family.
    adjusted = holm_adjust([
        row["p_raw"] for row in metric_results
    ])

    for row, adjusted_p in zip(metric_results, adjusted):
        row["p_holm"] = adjusted_p
        row["Significant (Holm, 0.05)"] = adjusted_p < 0.05
        test_rows.append(row)

table3 = pd.DataFrame(test_rows)

print("\n" + "=" * 150)
print("TABLE 3. EXACT MANN-WHITNEY U TESTS")
print("Holm correction applied separately within each metric.")
print("=" * 150)

print(
    table3[
        [
            "Metric",
            "Comparison",
            "n_first",
            "n_second",
            "U",
            "p_raw",
            "p_holm",
            "rank_biserial",
            "Significant (Holm, 0.05)",
        ]
    ].round(5).to_string(index=False)
)

# ============================================================
# 9. SAVE ALL TABLES
# ============================================================

run_results.to_csv("run_level_summaries.csv", index=False)
table2.to_csv("descriptive_summary_table.csv", index=False)
table3.to_csv("significance_tests.csv", index=False)

print("\n" + "=" * 100)
print("OUTPUT FILES CREATED")
print("=" * 100)
print("1. run_level_summaries.csv")
print("2. descriptive_summary_table.csv")
print("3. significance_tests.csv")

print("\nAnalysis complete.")
print(
    "\nImportant: Disabled GC results are descriptive only because "
    "those runs terminate early with MemoryError."
)
print(
    "GC overhead is calculated as total GC duration divided by "
    "total elapsed time, multiplied by 100. Interpret it cautiously "
    "if the timing boundaries differ between measurements."
)
