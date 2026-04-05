# OpenAI Tokenizer Encodings
---

## `r50k_base`
**Source:** https://openaipublic.blob.core.windows.net/encodings/r50k_base.tiktoken

**Models:**
- `text-davinci-002`, `text-davinci-003`
- Codex models (`code-cushman-001`, `code-davinci-001`)

---

## `p50k_base`
**Source:** https://openaipublic.blob.core.windows.net/encodings/p50k_base.tiktoken

**Models:**
- `code-davinci-002`

---

## `p50k_edit`
**Source:** https://openaipublic.blob.core.windows.net/encodings/p50k_base.tiktoken
(same file as `p50k_base`, different special tokens)

**Models:**
- `text-davinci-edit-001`
- `code-davinci-edit-001`

---

## `cl100k_base`
**Source:** https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken

**Models:**
- `gpt-3.5-turbo` and variants
- `gpt-4`, `gpt-4-32k`, `gpt-4-turbo`
- `text-embedding-ada-002`
- `text-embedding-3-small`, `text-embedding-3-large`

---

## `o200k_base`
**Source:** https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken

**Models:**
- `gpt-4o`, `gpt-4o-mini`
- `o1`, `o1-mini`
- `o3-mini`

---

## `o200k_harmony`
**Source:** same merge file as `o200k_base`, extended special token set (IDs 199998–201087)

**Models:** Internal/experimental, no public model uses this encoding.

---

## Vocab sizes

| Encoding        | Vocab size |
| -----------------| ------------|
| `r50k_base`     | 50,257    |
| `p50k_base`     | 50,281    |
| `p50k_edit`     | 50,284    |
| `cl100k_base`   | 100,277   |
| `o200k_base`    | 200,019   |
| `o200k_harmony` | ~201,088   |