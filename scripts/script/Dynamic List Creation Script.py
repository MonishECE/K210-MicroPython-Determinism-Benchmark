import time
import gc
import math


ITERATIONS = 1000

def listcreator():
    data = []

    for i in range(6):
        data.append([i])

    total = 0

    for item in data:
        total += item[0]

    return total



def percentile(sorted_data, p):
    idx = int((len(sorted_data) - 1) * p / 100)
    return sorted_data[idx]


def get_stats(results):
    n = len(results)

    mean = sum(results) / n
    minimum = min(results)
    maximum = max(results)

    variance = sum((x - mean) ** 2 for x in results) / n
    std_dev = math.sqrt(variance)

    cv = (std_dev / mean) * 100 if mean != 0 else 0

    sorted_results = sorted(results)

    p50 = percentile(sorted_results, 50)
    p95 = percentile(sorted_results, 95)
    p99 = percentile(sorted_results, 99)

    outliers = mean + (3 * std_dev)
    outliersC = 0
    for x in results:
        if x > outliers:
            outliersC += 1

    return (
        mean, minimum,maximum,std_dev,cv,p50,p95,p99,outliersC)


def run_benchmark(mode):

    if mode == "ENABLED":
        gc.enable()
    else:
        gc.disable()

    gc.collect()

    for _ in range(100):
        listcreator()

    results = []

    for _ in range(ITERATIONS):

        start = time.ticks_us()

        listcreator()

        elapsed = time.ticks_diff(time.ticks_us(), start)

        results.append(elapsed)


    (
        mean,
        minimum,
        maximum,
        std_dev,
        cv,
        p50,
        p95,
        p99,
        outliers
    ) = get_stats(results)



    print("Raw Data: ")
    print("BENCHMARK=Dynamic List Creation,GC=" + mode)

    for i in range(0, len(results), 50):
        print(",".join(str(x) for x in results[i:i+50]))

    print("RAW_DATA_END")


print("Dynamic List GC")


for mode in ["ENABLED", "DISABLED"]:
    run_benchmark(mode)
