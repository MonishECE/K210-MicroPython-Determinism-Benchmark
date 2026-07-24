import matplotlib.pyplot as plt
import numpy as np
import re

benchmarks = ['Bubble Sort', 'Matrix Multiply', 'Fibonacci', 'List Update', '4-Queens']
labels = ['a', 'b', 'c', 'd', 'e']

fig, axes = plt.subplots(3, 2, figsize=(12, 12))
axes = axes.flatten()

def get_numbers_from_file(filename):
    with open(filename, 'r') as f:
        content = f.read()
    numbers = re.findall(r'\d+', content)
    return np.array([float(n) for n in numbers])

for i, b in enumerate(benchmarks):
    data_e = np.sort(get_numbers_from_file(b + " GC Enabled Raw Data.txt"))
    data_d = np.sort(get_numbers_from_file(b + " GC Disabled Raw Data.txt"))
    
    axes[i].plot(data_e, np.linspace(0, 1, len(data_e)), label='GC Enabled')
    axes[i].plot(data_d, np.linspace(0, 1, len(data_d)), label='GC Disabled', linestyle='--')
    
    axes[i].text(0.05, 0.92, f'({labels[i]})', 
             transform=axes[i].transAxes, 
             fontweight='bold', 
             fontsize=12,
             bbox=dict(facecolor='white', alpha=0.3, edgecolor='none', pad=1))
    
    axes[i].set_xlabel('Time ($\mu s$)')
    axes[i].set_ylabel('CDF')
    axes[i].legend()
    axes[i].grid(True)

fig.delaxes(axes[5])
plt.tight_layout()
plt.subplots_adjust(top=0.95) 
plt.savefig('CDF Graph.jpg', dpi=300)
plt.show()
