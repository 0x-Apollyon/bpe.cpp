import tiktoken
import time
import argparse
import sys


#cli commands to match the cpp tokenizer, just single threaded
parser = argparse.ArgumentParser(description="GPT-4 Tiktoken Python Benchmark")
parser.add_argument("-i", "--input", required=True, help="Path to input text file")
parser.add_argument("-o", "--output", help="Path to output tokens file")
args = parser.parse_args()

try:
    #pre tokenization steps
    enc = tiktoken.get_encoding("cl100k_base")

    print(f"Reading input file: {args.input}", file=sys.stderr)
    with open(args.input, 'r', encoding='utf-8', errors='ignore') as f:
        text_data = f.read()


    print("Tokenizing...", file=sys.stderr)
    start_time = time.perf_counter()
    tokens = enc.encode(text_data, allowed_special=set())
    end_time = time.perf_counter()

    duration_ms = (end_time - start_time) * 1000
    print(f"Tokenized {len(tokens)} tokens in {duration_ms:.2f}ms", file=sys.stderr)

    token_output = " ".join(map(str, tokens))
    if args.output:
        with open(args.output, 'w') as f:
            f.write(token_output)
        print(f"Tokens saved to: {args.output}", file=sys.stderr)
    else:
        print(token_output)

except FileNotFoundError:
    print(f"Error: Could not find file {args.input}", file=sys.stderr)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
