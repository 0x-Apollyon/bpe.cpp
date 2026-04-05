import base64
import urllib.request
import time

OUTPUT_FILENAME = "gpt4_tokenizer_data.txt"
TIKTOKEN_URL = "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken"

print(f"Downloading {TIKTOKEN_URL}")
response = urllib.request.urlopen(TIKTOKEN_URL).read().decode('utf-8')
    
#the token_id is exactly equal to the tokens rank
vocab = {}
for line in response.splitlines():
    if not line: 
        continue
    b64_token, token_id = line.split()
    token_bytes = base64.b64decode(b64_token)
    vocab[token_bytes] = int(token_id)
        
print(f"Loaded {len(vocab)} tokens.")

#from ids to bytes
byte_to_id = {}
for i in range(256):
    b = bytes([i])
    byte_to_id[i] = vocab[b]


print("Reversing merges into (ID, ID) pairs")
start_time = time.time()
merges = {}
    
for token_bytes, token_id in vocab.items():

    if len(token_bytes) == 1:
        continue
            
    parts = []
    for b in token_bytes:
        parts.append(bytes([b]))
    
        
    #iterative merge
    while len(parts) > 2:
        min_rank = float('inf')
        min_idx = -1
            
        for i in range(len(parts) - 1):
            pair_bytes = parts[i] + parts[i+1]
            if pair_bytes in vocab:
                rank = vocab[pair_bytes]
                if rank < min_rank:
                    min_rank = rank
                    min_idx = i
                        
        #merge the highest priority pair
        parts[min_idx] = parts[min_idx] + parts[min_idx+1]
        parts.pop(min_idx + 1)
            
    id_left = vocab[parts[0]]
    id_right = vocab[parts[1]]
        
    merges[(id_left, id_right)] = token_id

    print(f"Reversed {len(merges)} merges in {time.time() - start_time:.2f}s.")

    
    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
        #first the 256 byte mappings
        f.write("[BYTE_MAP]\n")
        for b in range(256):
            f.write(f"{b} {byte_to_id[b]}\n")
            
        #then the merges
        f.write("[MERGES]\n")

        #sort by token_id to maintain ranks and priority
        sorted_merges = sorted(merges.items(), key=lambda x: x[1])
        for (id1, id2), token_id in sorted_merges:
            f.write(f"{id1} {id2} {token_id}\n")
            
    print(f"Merges file saved to{OUTPUT_FILENAME}")
