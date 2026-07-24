import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

folder = "."
results = []

for file in glob.glob(os.path.join(folder, "*.txt")):
    values = []
    with open(file, "r") as f:
        for line in f:
            numbers = line.strip().split(",")
            values.extend([float(x) for x in numbers if x.strip()])
    
    if not values:
        continue
    
    data = np.array(values)
    mean = np.mean(data)
    median = np.median(data)
    std = np.std(data, ddof=1)
    p95 = np.percentile(data, 95)
    p99 = np.percentile(data, 99)
    
    mad = np.median(np.abs(data - median))
    threshold = (3 * mad * 1.4826) + 1e-6
    outliers = data[np.abs(data - median) > threshold]
    outlier_count = len(outliers)
    
    base_name = os.path.basename(file).replace("Raw Data.txt", "").replace("GC ", "").strip()
    
    results.append({
        "Test Case": base_name,
        "Samples": len(data),
        "Max": round(np.max(data), 2),
        "Mean": round(mean, 2),
        "Median": round(median, 2),
        "Std Dev": round(std, 2),
        "CV (%)": round((std / mean) * 100 if mean != 0 else 0, 2),
        "P95": round(p95, 2),
        "P99": round(p99, 2),
        "Outliers (MAD)": outlier_count
    })

df = pd.DataFrame(results)

fig, ax = plt.subplots(figsize=(14, len(df) * 0.8))
ax.axis('off')

tbl = ax.table(
    cellText=df.values, 
    colLabels=df.columns, 
    loc='center', 
    cellLoc='center'
)

tbl.auto_set_font_size(False)
tbl.set_fontsize(10)
tbl.scale(1.2, 2.5)

for (row, col), cell in tbl.get_celld().items():
    if row == 0:
        cell.set_facecolor('#40466e')
        cell.set_text_props(color='white', weight='bold', fontsize=9)
    else:
        cell.set_facecolor('#f8f8f8')
        if col == 0:
            cell.set_text_props(fontsize=7)

plt.savefig("Statistics_Summary.jpg", bbox_inches='tight', dpi=300)
df.to_csv("Statistics_Summary.csv", index=False)
