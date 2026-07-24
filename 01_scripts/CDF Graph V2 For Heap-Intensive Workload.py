import matplotlib.pyplot as plt
import numpy as np
import re

benchmarks = ['Dynamic List Creation']

fig, ax = plt.subplots(figsize=(8, 6))

def get_numbers_from_file(filename):
    with open(filename, 'r') as f:
        content = f.read()
    numbers = re.findall(r'\d+', content)
    return np.array([float(n) for n in numbers])

b = benchmarks[0]
data_e = np.sort(get_numbers_from_file(b + " GC Enabled Raw Data.txt"))
data_d = np.sort(get_numbers_from_file(b + " GC Disabled Raw Data.txt"))

ax.plot(data_e, np.linspace(0, 1, len(data_e)), label='GC Enabled')
ax.plot(data_d, np.linspace(0, 1, len(data_d)), label='GC Disabled', linestyle='--')

ax.set_xlabel(r'Time ($\mu s$)')
ax.set_ylabel('CDF')
ax.legend()
ax.grid(True)

plt.tight_layout()
plt.savefig('CDF Graph For Heap Intensive.jpg', dpi=300)
plt.show()
