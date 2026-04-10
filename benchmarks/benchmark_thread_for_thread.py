import subprocess
import os
import urllib.request
import zipfile
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import re

#consts
CPP_EXE = "tokenizer.exe"
PY_SCRIPT = "tiktoken_bench_t4t.py"
DATA_URL = "http://mattmahoney.net/dc/enwik8.zip"
RAW_FILE = "enwik8"

#size scaling on fixed number of threads
SIZE_TESTS_MB = [1, 10, 30, 60, 100]

#thread scaling on fixed size
THREAD_TESTS = [1, 2, 4, 8, 12, 16]
THREAD_SCALING_SIZE_MB = 100

TRIALS = 3

# UI Aesthetic Constants
C_CPP = "#d63031"  # C++ Red
C_PY = "#0984e3"   # Py Blue
BG = "#0d1117"
FG = "#e6edf3"
GRD = "#21262d"


def download_dataset():
    if not os.path.exists(RAW_FILE):
        print("Downloading Enwik8 (100 MB Wikipedia)", flush=True)
        urllib.request.urlretrieve(DATA_URL, "enwik8.zip")
        with zipfile.ZipFile("enwik8.zip") as z:
            z.extractall()


def verify_outputs(cpp_file, py_file):
    try:
        with open(cpp_file) as f1, open(py_file) as f2:
            ct = f1.read().split()
            pt = f2.read().split()
        if len(ct) != len(pt):
            return False, f"Length Mismatch: C++={len(ct)}, Py={len(pt)}"
        return True, "Match"
    except Exception as e:
        return False, str(e)


def run_bench(cmd):
    times = []
    for _ in range(TRIALS):
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stderr + result.stdout
        m = re.search(r"in (\d+\.?\d*)ms", output)
        if m:
            times.append(float(m.group(1)))
    return sum(times) / len(times) if times else 0.0


def conduct_study():
    download_dataset()

    #size scaling
    print("\n" + "═"*75)
    print(f"{'PHASE 1: SIZE SCALING (Comparing 1T and Multi-Thread)':^75}")
    print("═"*75)
    header = f"{'Size (MB)':>10} │ {'Type':<10} │ {'C++ (ms)':>10} │ {'Py (ms)':>10} │ {'C++ MB/s':>12} │ {'Py MB/s':>12} │ {'Speedup':>10}"
    print(header)
    print("─"*75)

    size_results = []
    for sz in SIZE_TESTS_MB:
        fname = f"test_{sz}mb.txt"
        with open(RAW_FILE, "rb") as f:
            chunk = f.read(sz * 1024 * 1024)
        with open(fname, "wb") as f:
            f.write(chunk)

        # 1-Thread Comparison
        cpp1_ms = run_bench([CPP_EXE, "-i", fname, "-o", "out_cpp1.txt", "-t", "1"])
        py1_ms = run_bench(["python", PY_SCRIPT, "-i", fname, "-o", "out_py1.txt", "-t", "1"])
        
        # Max-Thread Comparison
        max_threads = os.cpu_count() or 4
        cppN_ms = run_bench([CPP_EXE, "-i", fname, "-o", "out_cppN.txt", "-t", str(max_threads)])
        pyN_ms = run_bench(["python", PY_SCRIPT, "-i", fname, "-o", "out_pyN.txt", "-t", str(max_threads)])

        # Verifications
        ok, msg = verify_outputs("out_cpp1.txt", "out_py1.txt")

        # Calculations
        mbps_cpp1 = sz / (cpp1_ms / 1000) if cpp1_ms > 0 else 0
        mbps_py1 = sz / (py1_ms / 1000) if py1_ms > 0 else 0
        mbps_cppN = sz / (cppN_ms / 1000) if cppN_ms > 0 else 0
        mbps_pyN = sz / (pyN_ms / 1000) if pyN_ms > 0 else 0

        su1 = py1_ms / cpp1_ms if cpp1_ms > 0 else 0
        suN = pyN_ms / cppN_ms if cppN_ms > 0 else 0

        print(f"{sz:>10} │ {'1-Thread':<10} │ {cpp1_ms:>10.1f} │ {py1_ms:>10.1f} │ {mbps_cpp1:>12.1f} │ {mbps_py1:>12.1f} │ {su1:>9.2f}x")
        print(f"{'':>10} │ {'Multi-T':<10} │ {cppN_ms:>10.1f} │ {pyN_ms:>10.1f} │ {mbps_cppN:>12.1f} │ {mbps_pyN:>12.1f} │ {suN:>9.2f}x")
        print("─"*75)

        size_results.append({
            "size": sz, "ok": ok, "msg": msg,
            "cpp1_ms": cpp1_ms, "py1_ms": py1_ms,
            "cppN_ms": cppN_ms, "pyN_ms": pyN_ms,
            "mbps_cpp1": mbps_cpp1, "mbps_py1": mbps_py1,
            "mbps_cppN": mbps_cppN, "mbps_pyN": mbps_pyN
        })

    # --- PHASE 2: Thread Scaling Matrix ---
    print("\n" + "═"*75)
    print(f"{'PHASE 2: THREAD SCALING (At fixed ' + str(THREAD_SCALING_SIZE_MB) + ' MB)':^75}")
    print("═"*75)
    header = f"{'Threads':>10} │ {'C++ (ms)':>12} │ {'Py (ms)':>12} │ {'C++ MB/s':>12} │ {'Py MB/s':>12} │ {'Speedup':>10}"
    print(header)
    print("─"*75)

    thread_results = []
    fname_100 = f"test_{THREAD_SCALING_SIZE_MB}mb.txt"

    for t in THREAD_TESTS:
        cpp_ms = run_bench([CPP_EXE, "-i", fname_100, "-o", "out_cpp.txt", "-t", str(t)])
        py_ms = run_bench(["python", PY_SCRIPT, "-i", fname_100, "-o", "out_py.txt", "-t", str(t)])

        mbps_cpp = THREAD_SCALING_SIZE_MB / (cpp_ms / 1000) if cpp_ms > 0 else 0
        mbps_py = THREAD_SCALING_SIZE_MB / (py_ms / 1000) if py_ms > 0 else 0
        su = py_ms / cpp_ms if cpp_ms > 0 else 0

        print(f"{t:>10} │ {cpp_ms:>12.1f} │ {py_ms:>12.1f} │ {mbps_cpp:>12.1f} │ {mbps_py:>12.1f} │ {su:>9.2f}x")
        thread_results.append({
            "threads": t, "cpp_ms": cpp_ms, "py_ms": py_ms,
            "mbps_cpp": mbps_cpp, "mbps_py": mbps_py
        })
    print("─"*75)

    return size_results, thread_results


def plot_results(size_rows, thread_rows):
    plt.rcParams.update({
        "figure.facecolor": BG, "axes.facecolor": BG,
        "axes.edgecolor": GRD, "axes.labelcolor": FG,
        "xtick.color": FG, "ytick.color": FG,
        "grid.color": GRD, "text.color": FG,
        "legend.facecolor": "#161b22", "legend.edgecolor": GRD,
        "font.family": "sans-serif"
    })

    fig = plt.figure(figsize=(18, 12))
    fig.suptitle("True Thread-for-Thread Comparison: C++ vs OpenAI tiktoken (Enwik8)", fontsize=16, y=0.97)

    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.35, wspace=0.3)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[0, 2])
    ax4 = fig.add_subplot(gs[1, 0])
    ax5 = fig.add_subplot(gs[1, 1])
    ax6 = fig.add_subplot(gs[1, 2])

    sizes = [r["size"] for r in size_rows]
    threads = [r["threads"] for r in thread_rows]

    # Chart 1: Latency (Size Scaling)
    ax1.plot(sizes, [r["cpp1_ms"] for r in size_rows], color=C_CPP, label="C++ (1T)", marker="o")
    ax1.plot(sizes, [r["py1_ms"] for r in size_rows], color=C_PY, label="tiktoken (1T)", marker="o", ls="--")
    ax1.plot(sizes, [r["cppN_ms"] for r in size_rows], color=C_CPP, label="C++ (Multi-T)", marker="s", alpha=0.6)
    ax1.plot(sizes, [r["pyN_ms"] for r in size_rows], color=C_PY, label="tiktoken (Multi-T)", marker="s", ls="--", alpha=0.6)
    ax1.set(title="Data Size vs Latency", xlabel="Size (MB)", ylabel="Time (ms)")
    ax1.legend(fontsize=8)
    ax1.grid(True, ls="--", alpha=0.3)

    # Chart 2: Throughput (Size Scaling)
    ax2.plot(sizes, [r["mbps_cpp1"] for r in size_rows], color=C_CPP, label="C++ (1T)", marker="o")
    ax2.plot(sizes, [r["mbps_py1"] for r in size_rows], color=C_PY, label="tiktoken (1T)", marker="o", ls="--")
    ax2.plot(sizes, [r["mbps_cppN"] for r in size_rows], color=C_CPP, label="C++ (Multi-T)", marker="s", alpha=0.6)
    ax2.plot(sizes, [r["mbps_pyN"] for r in size_rows], color=C_PY, label="tiktoken (Multi-T)", marker="s", ls="--", alpha=0.6)
    ax2.set(title="Data Size vs Throughput", xlabel="Size (MB)", ylabel="MB / s")
    ax2.grid(True, ls="--", alpha=0.3)

    # Chart 3: Speedup vs Size
    ax3.plot(sizes, [r["py1_ms"]/r["cpp1_ms"] for r in size_rows], color=C_CPP, label="1T Speedup", marker="o")
    ax3.plot(sizes, [r["pyN_ms"]/r["cppN_ms"] for r in size_rows], color=C_PY, label="Multi-T Speedup", marker="s")
    ax3.axhline(1.0, color=FG, ls=":", alpha=0.5)
    ax3.set(title="Speedup Factor (Data Size)", xlabel="Size (MB)", ylabel="Multiplier (C++ / Tiktoken)")
    ax3.legend(fontsize=8)
    ax3.grid(True, ls="--", alpha=0.3)

    # Chart 4: Thread Scaling (Fixed 100MB) Latency
    ax4.plot(threads, [r["cpp_ms"] for r in thread_rows], color=C_CPP, label="C++", marker="o")
    ax4.plot(threads, [r["py_ms"] for r in thread_rows], color=C_PY, label="tiktoken", marker="s", ls="--")
    ax4.set(title=f"Threads vs Time ({THREAD_SCALING_SIZE_MB}MB)", xlabel="Thread Count", ylabel="Time (ms)")
    ax4.legend(fontsize=8)
    ax4.grid(True, ls="--", alpha=0.3)

    # Chart 5: Thread Scaling (Fixed 100MB) Throughput
    ax5.plot(threads, [r["mbps_cpp"] for r in thread_rows], color=C_CPP, label="C++", marker="o")
    ax5.plot(threads, [r["mbps_py"] for r in thread_rows], color=C_PY, label="tiktoken", marker="s", ls="--")
    ax5.set(title=f"Threads vs Throughput ({THREAD_SCALING_SIZE_MB}MB)", xlabel="Thread Count", ylabel="Throughput (MB/s)")
    ax5.legend(fontsize=8)
    ax5.grid(True, ls="--", alpha=0.3)

    # Chart 6: Scalability Ratio
    # Amdahl's efficiency: Throughput_N / (N * Throughput_1)
    base_cpp = thread_rows[0]["mbps_cpp"]
    base_py = thread_rows[0]["mbps_py"]
    cpp_eff = [r["mbps_cpp"] / (r["threads"] * base_cpp) for r in thread_rows]
    py_eff = [r["mbps_py"] / (r["threads"] * base_py) for r in thread_rows]

    ax6.plot(threads, cpp_eff, color=C_CPP, label="C++ Parallel Efficiency", marker="o")
    ax6.plot(threads, py_eff, color=C_PY, label="tiktoken Parallel Efficiency", marker="s", ls="--")
    ax6.set(title="Parallel Efficiency (Amdahl's Decay)", xlabel="Thread Count", ylabel="Efficiency (Scaled Work / Ideal)")
    ax6.legend(fontsize=8)
    ax6.grid(True, ls="--", alpha=0.3)

    plt.savefig("fair_benchmarks.png", dpi=200, bbox_inches="tight")
    plt.show()


size_rows, thread_rows = conduct_study()
plot_results(size_rows, thread_rows)