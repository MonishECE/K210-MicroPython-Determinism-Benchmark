import os
import statistics
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import mannwhitneyu


def load_data(filename):
    with open(filename, "r") as f:
        text = f.read()

    data = []

    for value in text.replace("\n", ",").split(","):
        value = value.strip()
        if value:
            data.append(int(value))

    return data


benchmarks = [
    "List Creation",
    "Fibonacci",
    "List Update",
    "Matrix Multiply",
    "Bubble Sort",
    "4-Queens",
]


alpha = 0.05

print("\n========== MANN-WHITNEY U ANALYSIS ==========\n")


table_rows = []


for benchmark in benchmarks:

    enabled_file = benchmark + " GC Enabled Raw Data.txt"
    disabled_file = benchmark + " GC Disabled Raw Data.txt"

    if not os.path.exists(enabled_file):
        print("Missing:", enabled_file)
        continue

    if not os.path.exists(disabled_file):
        print("Missing:", disabled_file)
        continue


    enabled = load_data(enabled_file)
    disabled = load_data(disabled_file)


    n1 = len(enabled)
    n2 = len(disabled)


    U, p = mannwhitneyu(
        enabled,
        disabled,
        alternative="two-sided",
        method="asymptotic"
    )


    rbc = (2 * U) / (n1 * n2) - 1


    median_enabled = statistics.median(enabled)
    median_disabled = statistics.median(disabled)

    median_difference = median_enabled - median_disabled


    if median_enabled > median_disabled:
        higher_median = "GC Enabled"
    elif median_disabled > median_enabled:
        higher_median = "GC Disabled"
    else:
        higher_median = "Equal"


    abs_rbc = abs(rbc)

    if abs_rbc < 0.10:
        effect = "Negligible"
    elif abs_rbc < 0.30:
        effect = "Small"
    elif abs_rbc < 0.50:
        effect = "Moderate"
    else:
        effect = "Large"


    result = (
        "Significant"
        if p < alpha
        else "Not Significant"
    )


    print("-------------------------------------------")
    print("Benchmark:", benchmark)
    print("Samples:", n1, "vs", n2)
    print("U Statistic:", round(U, 2))
    print("P-value:", "{:.6g}".format(p))
    print("Rank-Biserial Correlation:", round(rbc, 4))
    print("Effect Size:", effect)
    print("Median Difference:", median_difference, "us")
    print("Higher Median:", higher_median)
    print("Result:", result)


    table_rows.append(
        {
            "Benchmark": benchmark,
            "Samples": f"{n1} vs {n2}",
            "U Statistic": f"{U:,.1f}",
            "P-value": "{:.2e}".format(p),
            "Rank-Biserial": f"{rbc:.4f}",
            "Effect Size": effect,
            "Median Difference (us)": median_difference,
            "Higher Median": higher_median,
            "Result": result,
        }
    )


if table_rows:

    df = pd.DataFrame(table_rows)

    df.to_csv(
        "mann_whitney_results.csv",
        index=False
    )


    fig, ax = plt.subplots(figsize=(14, 4))

    ax.axis("tight")
    ax.axis("off")


    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc="center",
        loc="center"
    )


    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.8)


    plt.title(
        "Mann-Whitney U Test Results",
        fontsize=14,
        weight="bold"
    )


    plt.savefig(
        "mann_whitney_table.png",
        dpi=300,
        bbox_inches="tight"
    )



