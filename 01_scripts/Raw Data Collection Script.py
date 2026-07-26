import time
import gc
import math
# Algorithm for Bubble Sort, using a list with 20 fixed selected elements.
def BubbleSort():
   data = [64, 34, 25, 12, 22, 11, 90, 5, 1, 77, 88, 33, 17, 42, 56, 73, 18, 29, 44, 91]
   n = len(data)
   for i in range(n):
       for j in range(n - i - 1):
           if data[j] > data[j + 1]:
               data[j], data[j + 1] = data[j + 1], data[j]
# Algorithm for Matrix Multiplication, with a 8x8 size, matrix_C = matrix_A * matrix_B
def matrix8x8():
   for i in range(8):
       for j in range(8):
           total = 0
           for k in range(8):
               total += matrix_A[i][k] * matrix_B[k][j]
           matrix_C[i][j] = total
# Algorithm for Fibonacci series of 25 numbers, starting with 0 and 1.
def fibonacciIt():
   a = 0
   b = 1
   for _ in range(25):
       temp = a
       a = b
       b = temp + b

# Algorithm for listUpdate, perform sequential write on a preallocated 500-element list.
def listUpdate():
   for i in range(500):
       list_data[i] = i
      
# Algorithm for the n-Queens problem, placing n queens on an n x n board and finding the first valid solution.
# No two queens can be in the same column, row, or diagonal
# n = 4 for this benchmark, so creates a 4x4 chessboard.
def FourQueens():
   n = 4
   for i in range(n): board[i] = -1
   row, col = 0, 0
   while row < n:
       found = False
       while col < n:
           is_safe = True
           for prev_row in range(row):
               prev_col = board[prev_row]
               if prev_col == col or prev_col - prev_row == col - row or prev_col + prev_row == col + row:
                   is_safe = False
                   break
           if is_safe:
               board[row] = col
               col = 0
               found = True
               break
           else:
               col += 1
       if found:
           row += 1
           if row == n: return
       else:
           row -= 1
           if row < 0: return
           col = board[row] + 1

ITERATIONS = 1000
# Declares matrices, list_data , and board with intial values once.  
# Avoids repeated memory allocation during benchmark execution.
matrix_A = [[i + j for j in range(8)] for i in range(8)]
matrix_B = [[i * j for j in range(8)] for i in range(8)]
matrix_C = [[0] * 8 for _ in range(8)]
list_data = [i for i in range(500)]
board = [-1] * 4

# calculates percentiles
def percentile(sorted_data, p):
   idx = int((len(sorted_data) - 1) * p / 100)
   return sorted_data[idx]

# calculates statistics for measurements (not used in the technical note for analysis)
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
   outlier_threshold = mean + (3 * std_dev)
   outliers = 0
   for x in results:
       if x > outlier_threshold:
           outliers += 1
   return (mean, minimum, maximum, std_dev, cv, p50, p95, p99, outliers)

# Runs a benchmark under a selected GC state, collects execution-time samples, calculates statistics, and outputs raw timing data.
def run_benchmark(name, func, mode):
   if mode == "ENABLED":
       gc.enable()
   else:
       gc.disable()
   gc.collect()   
# Executes algorithm 100 times before the actual run for execution times as a warm-up to account for cold start effects
   for _ in range(100):
       try:
           func()
       except:
           pass

   results = []
   try:
# Run each algorithm for 1000 times per GC state amd captures execution times
       for _ in range(ITERATIONS):
          
# MicroPythons microsecond based counter to measure execution times.
           start = time.ticks_us()
           func()
           elapsed = time.ticks_diff(time.ticks_us(), start)
           results.append(elapsed)
   except Exception:
       return

   (mean, mn, mx, std, cv, p50, p95, p99, outliers) = get_stats(results)

   print("\n--- " + name + " | GC: " + mode + " ---")
   print("Mean: " + str(mean) + " us")
   print("Min: " + str(mn) + " us")
   print("Max: " + str(mx) + " us")
   print("Std Dev: " + str(std) + " us")
   print("CV: " + str(cv) + " %")
   print("Median: " + str(p50) + " us")
   print("P95: " + str(p95) + " us")
   print("P99: " + str(p99) + " us")
   print("Outliers: " + str(outliers))
   print("RAW_DATA_BEGIN")
   print("BENCHMARK=" + name + ",GC=" + mode)

   for i in range(0, len(results), 50):
       print(",".join(str(x) for x in results[i:i+50]))

   print("RAW_DATA_END")
# defining benchmarks list with all algorithm name and corresponding function name
benchmarks = [
   ("Bubble Sort", BubbleSort),
   ("Matrix Multiply", matrix8x8),
   ("Fibonacci", fibonacciIt),
   ("List Update", listUpdate),
   ("4 Queens", FourQueens)
]
# Main execution starts here, runs all algorithm functions under each GC configuration (enabled and disabled).
print("STARTING DETERMINISM ANALYSIS")
for mode in ["ENABLED", "DISABLED"]:
   for name, func in benchmarks:
       run_benchmark(name, func, mode)

