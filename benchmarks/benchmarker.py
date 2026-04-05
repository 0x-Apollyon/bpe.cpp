import subprocess
import os
import urllib.request
import zipfile
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import re

CPP_EXE      = "tokenizer.exe"
PY_SCRIPT    = "tiktoken_bench.py"
DATA_URL     = "http://mattmahoney.net/dc/enwik8.zip"
RAW_FILE     = "enwik8"
TEST_SIZES_MB = [1, 10, 20, 30, 50, 60, 80, 100]
TRIALS       = 3


def download_dataset():
    if not os.path.exists(RAW_FILE):
        print("Downloading Enwik8 (100 MB Wikipedia)", flush=True)
        urllib.request.urlretrieve(DATA_URL, "enwik8.zip")
        with zipfile.ZipFile("enwik8.zip") as z:
            z.extractall()
        print("Download complete.", flush=True)


def count_tokens(path):
    with open(path, "r") as f:
        return len(f.read().split())


def verify_outputs(cpp_file, py_file):
    try:
        with open(cpp_file) as f1, open(py_file) as f2:
            ct = f1.read().split()
            pt = f2.read().split()
        if len(ct) != len(pt):
            return False, f"Length Mismatch: C++={len(ct)}, Python={len(pt)}"
        for i, (a, b) in enumerate(zip(ct, pt)):
            if a != b:
                return False, f"ID Mismatch at index {i}: C++='{a}', Python='{b}'"
        return True, "Perfect Match"
    except Exception as e:
        return False, str(e)


def run_bench(cmd):
    """Run cmd TRIALS times and return (avg_ms, min_ms, max_ms)."""
    times = []
    for _ in range(TRIALS):
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stderr + result.stdout
        m = re.search(r"in (\d+\.?\d*)ms", output)
        if m:
            times.append(float(m.group(1)))
    if not times:
        return 0.0, 0.0, 0.0
    return sum(times) / len(times), min(times), max(times)


def conduct_study():
    download_dataset()

    rows = []   # list of dicts, one per size

    header = (f"{'Size':>6} │ {'Status':<14} │ "
              f"{'C++ 1T ms':>10} │ {'C++ MT ms':>10} │ {'Py ms':>10} │ "
              f"{'C++ 1T MB/s':>12} │ {'C++ MT MB/s':>12} │ {'Py MB/s':>10} │ "
              f"{'Speedup 1T':>10} │ {'Speedup MT':>10}")
    print("\n" + "═" * len(header))
    print(header)
    print("─" * len(header))

    for size in TEST_SIZES_MB:
        fname   = f"test_{size}mb.txt"
        cpp_out = "out_cpp.txt"
        py_out  = "out_py.txt"

        # create slice
        with open(RAW_FILE, "rb") as f:
            chunk = f.read(size * 1024 * 1024)
        with open(fname, "wb") as f:
            f.write(chunk)

        # ── benchmarks ──
        avg_cpp1, min_cpp1, max_cpp1 = run_bench([CPP_EXE, "-i", fname, "-o", cpp_out, "-t", "1"])
        avg_cppN, min_cppN, max_cppN = run_bench([CPP_EXE, "-i", fname, "-o", cpp_out])
        avg_py,   min_py,   max_py   = run_bench(["python", PY_SCRIPT, "-i", fname, "-o", py_out])

        # ── token counts & verification (single-thread run for correctness) ──
        run_bench([CPP_EXE, "-i", fname, "-o", cpp_out, "-t", "1"])   # fresh output
        ok, msg = verify_outputs(cpp_out, py_out)
        token_count = count_tokens(py_out)

        #stats counters
        def mbps(ms): 
            if ms > 0:
                return (size / (ms / 1000))
            else:
                return 0

        def tps(ms):  
            if ms > 0:
                return (token_count / (ms / 1000))
            else:
                return 0

        def speedup(base, cmp): 
            if cmp > 0:
                return base/cmp
            else:
                return 0

        if ok:
            status_str = "PASS"
        else:
            status_str = "FAIL"

        row = dict(
            size=size,
            ok=ok, msg=msg,
            avg_cpp1=avg_cpp1, min_cpp1=min_cpp1, max_cpp1=max_cpp1,
            avg_cppN=avg_cppN, min_cppN=min_cppN, max_cppN=max_cppN,
            avg_py=avg_py,     min_py=min_py,     max_py=max_py,
            tokens=token_count,
            mbps_cpp1=mbps(avg_cpp1), mbps_cppN=mbps(avg_cppN), mbps_py=mbps(avg_py),
            tps_cpp1=tps(avg_cpp1),   tps_cppN=tps(avg_cppN),   tps_py=tps(avg_py),
            su1=speedup(avg_py, avg_cpp1),
            suN=speedup(avg_py, avg_cppN),
        )
        rows.append(row)

        print(f"{size:>6} │ {status_str:<14} │ "
              f"{avg_cpp1:>10.1f} │ {avg_cppN:>10.1f} │ {avg_py:>10.1f} │ "
              f"{row['mbps_cpp1']:>12.1f} │ {row['mbps_cppN']:>12.1f} │ {row['mbps_py']:>10.1f} │ "
              f"{row['su1']:>10.2f}x │ {row['suN']:>10.2f}x")

        if not ok:
            print(f"        {msg}")

    print("-" * len(header))
    return rows



#plotting
def plot_results(rows):
    sizes     = [r["size"]      for r in rows]
    cpp1_ms   = [r["avg_cpp1"]  for r in rows]
    cppN_ms   = [r["avg_cppN"]  for r in rows]
    py_ms     = [r["avg_py"]    for r in rows]
    cpp1_mbps = [r["mbps_cpp1"] for r in rows]
    cppN_mbps = [r["mbps_cppN"] for r in rows]
    py_mbps   = [r["mbps_py"]   for r in rows]
    su1       = [r["su1"]       for r in rows]
    suN       = [r["suN"]       for r in rows]
    tps_cpp1  = [r["tps_cpp1"]  for r in rows]
    tps_cppN  = [r["tps_cppN"]  for r in rows]
    tps_py    = [r["tps_py"]    for r in rows]

    # error bars: half the (max-min) spread
    def err(key_min, key_max):
        return [abs(r[key_max] - r[key_min]) / 2 for r in rows]

    e_cpp1 = err("min_cpp1", "max_cpp1")
    e_cppN = err("min_cppN", "max_cppN")
    e_py   = err("min_py",   "max_py")

    C1  = "#e07b39"   # C++ 1-thread  – warm orange
    CN  = "#d63031"   # C++ multi-thread – red
    PY  = "#0984e3"   # Python / tiktoken – blue
    BG  = "#0d1117"
    FG  = "#e6edf3"
    GRD = "#21262d"

    plt.rcParams.update({
        "figure.facecolor": BG, "axes.facecolor": BG,
        "axes.edgecolor": GRD, "axes.labelcolor": FG,
        "xtick.color": FG, "ytick.color": FG,
        "grid.color": GRD, "text.color": FG,
        "legend.facecolor": "#161b22", "legend.edgecolor": GRD,
        "font.family": "monospace",
    })

    fig = plt.figure(figsize=(18, 13), facecolor=BG)
    fig.suptitle("C++ Tokenizer vs OpenAI tiktoken  ·  Enwik8 benchmark",
                 fontsize=15, color=FG, y=0.98, fontfamily="monospace")

    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.42, wspace=0.35)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[0, 2])
    ax4 = fig.add_subplot(gs[1, 0])
    ax5 = fig.add_subplot(gs[1, 1])
    ax6 = fig.add_subplot(gs[1, 2])

    kw = dict(linewidth=2, marker="o", markersize=5)

    #latency
    ax1.errorbar(sizes, cpp1_ms, yerr=e_cpp1, color=C1, label="C++ 1-thread",   fmt="o-", **{k:v for k,v in kw.items() if k not in ("linewidth","marker","markersize")}, linewidth=2, markersize=5, capsize=3)
    ax1.errorbar(sizes, cppN_ms, yerr=e_cppN, color=CN, label="C++ multi-thread", fmt="s-", linewidth=2, markersize=5, capsize=3)
    ax1.errorbar(sizes, py_ms,   yerr=e_py,   color=PY, label="tiktoken (Py)",   fmt="^--",linewidth=2, markersize=5, capsize=3)
    ax1.set(title="Latency  (lower = better)", xlabel="Input (MB)", ylabel="Time (ms)")
    ax1.legend(fontsize=8)
    ax1.grid(True, ls="--", alpha=0.4)

    #throughput
    ax2.plot(sizes, cpp1_mbps, color=C1, label="C++ 1-thread", **kw)
    ax2.plot(sizes, cppN_mbps, color=CN, label="C++ multi-thread", marker="s", linewidth=2, markersize=5)
    ax2.plot(sizes, py_mbps,   color=PY, label="tiktoken (Py)",    marker="^", linewidth=2, markersize=5, ls="--")
    ax2.set(title="Throughput  (higher = better)", xlabel="Input (MB)", ylabel="MB / s")
    ax2.legend(fontsize=8)
    ax2.grid(True, ls="--", alpha=0.4)

    #tokens per second
    ax3.plot(sizes, [t/1e6 for t in tps_cpp1], color=C1, label="C++ 1-thread", **kw)
    ax3.plot(sizes, [t/1e6 for t in tps_cppN], color=CN, label="C++ multi-thread", marker="s", linewidth=2, markersize=5)
    ax3.plot(sizes, [t/1e6 for t in tps_py],   color=PY, label="tiktoken (Py)",    marker="^", linewidth=2, markersize=5, ls="--")
    ax3.set(title="Tokens / sec  (higher = better)", xlabel="Input (MB)", ylabel="M tokens / s")
    ax3.legend(fontsize=8)
    ax3.grid(True, ls="--", alpha=0.4)

    #speedup
    ax4.plot(sizes, su1, color=C1, label="C++ 1T  vs tiktoken", **kw)
    ax4.plot(sizes, suN, color=CN, label="C++ MT  vs tiktoken", marker="s", linewidth=2, markersize=5)
    ax4.axhline(1.0, color=FG, ls=":", lw=1, alpha=0.5)
    ax4.set(title="Speedup vs tiktoken  (higher = better)", xlabel="Input (MB)", ylabel="× faster")
    ax4.legend(fontsize=8)
    ax4.grid(True, ls="--", alpha=0.4)

    #grouped bars
    key_sizes  = [1, 10, 50, 100]
    key_idx    = [TEST_SIZES_MB.index(s) for s in key_sizes if s in TEST_SIZES_MB]
    bar_labels = [f"{TEST_SIZES_MB[i]} MB" for i in key_idx]
    x = np.arange(len(key_idx))
    w = 0.25
    ax5.bar(x - w,   [cpp1_mbps[i] for i in key_idx], w, color=C1, alpha=0.9, label="C++ 1T")
    ax5.bar(x,       [cppN_mbps[i] for i in key_idx], w, color=CN, alpha=0.9, label="C++ MT")
    ax5.bar(x + w,   [py_mbps[i]   for i in key_idx], w, color=PY, alpha=0.9, label="tiktoken")
    ax5.set_xticks(x)
    ax5.set_xticklabels(bar_labels)
    ax5.set(title="Throughput at key sizes", xlabel="File size", ylabel="MB / s")
    ax5.legend(fontsize=8)
    ax5.grid(True, axis="y", ls="--", alpha=0.4)

    #correctness table
    ax6.axis("off")
    col_labels = ["Size", "Tokens", "Match?"]
    table_data = [
        [f"{r['size']} MB",
         f"{r['tokens']:,}",
         "Matching" if r["ok"] else f"Incorrect {r['msg'][:30]}"]
        for r in rows
    ]
    tbl = ax6.table(cellText=table_data, colLabels=col_labels,
                    cellLoc="center", loc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1.1, 1.5)

    for (row_i, col_i), cell in tbl.get_celld().items():
        cell.set_facecolor("#161b22" if row_i > 0 else "#21262d")
        cell.set_text_props(color=FG)
        cell.set_edgecolor(GRD)

    ax6.set_title("Correctness", color=FG, pad=10)

    plt.savefig("performance_comparison.png", dpi=150, bbox_inches="tight", facecolor=BG)
    print("\nGraph saved at performance_comparison.png")
    plt.show()



if __name__ == "__main__":
    rows = conduct_study()
    plot_results(rows)