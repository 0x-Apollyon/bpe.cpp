# bpe.cpp

A fast BPE tokenizer which supports many encodings, written in C++. Reads a text file and outputs a space separated list of token IDs.

1.5x faster than OpenAI's [tiktoken](https://github.com/openai/tiktoken) in most cases. (thread-for-thread)

<img width="351" height="411" alt="image" src="https://github.com/user-attachments/assets/1b61efcf-c677-49ff-9797-0c6ddd9d6f62" />


---

## Requirements

- Windows x64
- [PCRE2](https://github.com/PCRE2Project/pcre2) (static build via vcpkg)
- MSVC (`cl.exe`)

---

## Building

**1. Install PCRE2 via vcpkg**
```
vcpkg install pcre2:x64-windows-static
```

**2. Compile**
```
cl.exe /EHsc /O2 /Oi /Ot /GL /MT /std:c++17 tokenizer.cpp /I vcpkg\installed\x64-windows-static\include /link /LIBPATH:vcpkg\installed\x64-windows-static\lib pcre2-8.lib advapi32.lib user32.lib /LTCG /OUT:tokenizer.exe
```

Or download a prebuilt binary present in the binaries directory

---

## Usage

```
tokenizer.exe -i <input_file> -o <output_file> [options]
```

| Flag | Description | Default |
|---|---|---|
| `-i` | Input text file | required |
| `-o` | Output token ID file | required |
| `-m` | Merge list file | `gpt4_tokenizer_data.txt` |
| `-s` | Special tokens file | `special.txt` |
| `-t` | Thread count | auto |

**Example**
```
tokenizer.exe -i document.txt -o tokens.txt
tokenizer.exe -i document.txt -o tokens.txt -t 8
```

The output is a space separated sequence of integer token IDs, one token per space.

---

## Required Files

These files must be in the same directory as the binary (or passed explicitly via `-m` and `-s`):

- **`gpt4_tokenizer_data.txt`**: byte map and merge list, converted from the OpenAI `.tiktoken` file
- **`special.txt`**: special token definitions (ex: `<|endoftext|>`). Leave empty if not needed.

See the [Converters](#converters) section to generate these from an OpenAI encoding.

---

## Converters

OpenAI's `.tiktoken` files represent merges as raw bytes. This tokenizer uses integer IDs internally, so the merge file needs to be converted before use.

**1. Set the source URL and output filename in `convert.py`**
Pick a URL from `oai_links.txt`.

**2. Run `convert.py`**
```
python convert.py
```
The output file can then be passed directly via `-m`.

---

## Benchmarks

Benchmarks compare this tokenizer against tiktoken on the [Enwik8](http://mattmahoney.net/dc/textdata.html) dataset (100 MB Wikipedia corpus).

<img width="1220" height="422" alt="image" src="https://github.com/user-attachments/assets/0bff1e91-81a0-48e2-a157-5469eaeac976" />


---
