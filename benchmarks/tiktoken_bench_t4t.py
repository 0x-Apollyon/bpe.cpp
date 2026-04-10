import tiktoken
import time
import argparse

#cli arguments
parser = argparse.ArgumentParser(description="GPT-4 Tiktoken Python Benchmark")
parser.add_argument("-i", "--input", required=True, help="Path to input text file")
parser.add_argument("-o", "--output", help="Path to output tokens file")
parser.add_argument("-t", "--threads", type=int, default=1, help="Thread count")
args = parser.parse_args()

try:
    enc = tiktoken.get_encoding("cl100k_base")

    with open(args.input, 'r', encoding='utf-8', errors='ignore') as f:
        text_data = f.read()

    lines = text_data.splitlines(keepends=True)
    num_threads = args.threads
    
    #N buckets one for each thread
    chunk_size = max(1, len(lines) // num_threads)
    chunks = ["".join(lines[i:i + chunk_size]) for i in range(0, len(lines), chunk_size)]

    #start measuring time
    start_time = time.perf_counter()
    
    if num_threads <= 1:
        tokens = enc.encode(text_data, allowed_special=set())
    else:
        batch_tokens = enc.encode_batch(chunks, num_threads=num_threads, allowed_special=set())
        tokens = []
        for sublist in batch_tokens:
            for token in sublist:
                tokens.append(token)

        
    end_time = time.perf_counter()


    duration_ms = (end_time - start_time) * 1000
    print(f"in {duration_ms:.2f}ms")

    if args.output and args.output != "NUL":
        with open(args.output, 'w') as f:
            f.write(" ".join(map(str, tokens)))

except Exception as e:
    print(f"Error: {e}")