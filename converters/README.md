## Converters

OpenAI's `.tiktoken` merge files represent token merges as raw bytes rather than integer IDs. This tokenizer works with integer IDs internally, so the merge file needs to be translated before use.

**1. Set the source and output paths in `convert.py`**
Pick a `.tiktoken` URL from `oai_links.md` (or any source of your choice) and set a output filename.

**2. Run `convert.py`**
The output file can be used directly as your merges file.