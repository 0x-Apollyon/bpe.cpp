## Benchmarks

**1. Build or download the tokenizer**
Compile from source using the instructions provided in the root directory, or use a prebuilt binary from the binaries directory

**2. Install Python dependencies**
```
pip install -r requirements.txt
```
`uv` works too just replace `pip` with `uv pip`.

**3. Place the required files in the same directory as the script**
- Merge list ex: `gpt4_tokenizer_data.txt`
- Special tokens ex: `special.txt` (leave empty if no special tokens)
- tiktoken reference script ex: `tiktoken_bench.py` or `tiktoken_bench_t4t.py`

**4. Run**
```
python bench.py //best case comparison
python benchmark_thread_for_thread.py //thread for thread scaling and sizing comparison
```