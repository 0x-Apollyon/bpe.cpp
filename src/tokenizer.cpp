#define PCRE2_STATIC
#define PCRE2_CODE_UNIT_WIDTH 8
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN

#define CACHE_SIZE 100000
#define CACHE_SIZE_MAX 200000
//keeping it somewhere close to the vocab size of a model

#include <iostream>
#include <fstream>
#include <string>
#include <string_view>
#include <vector>
#include <unordered_map>
#include <chrono>
#include <climits>
#include <charconv>
#include <thread>
#include <windows.h>
#include <pcre2.h>

//regex helper function
std::string escape_regex(const std::string& s) {
    std::string out;
    for (char c : s) {
        if (strchr(".^$*+?()[]{}\\|", c)){
            out = out + "\\";
        }
        out = out + c;
    }
    return out;
}

//windows memory mapper
class WindowsMMap {
    private:
        HANDLE hFile = INVALID_HANDLE_VALUE;
        HANDLE hMapping = NULL;
        void* mapped_data = nullptr;
        size_t file_size = 0;

    public:
        
        //open memory map to the file using windowsAPI
        WindowsMMap(const std::string& filepath) {
            hFile = CreateFileA(filepath.c_str(), GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
            
            if (hFile == INVALID_HANDLE_VALUE){
                throw std::runtime_error("Failed to open file.");
            }

            LARGE_INTEGER size;
            GetFileSizeEx(hFile, &size);
            file_size = size.QuadPart;

            if (file_size > 0) {
                hMapping = CreateFileMappingA(hFile, NULL, PAGE_READONLY, 0, 0, NULL);
                mapped_data = MapViewOfFile(hMapping, FILE_MAP_READ, 0, 0, 0);
            }
        }
        
        //close everything to prevent resource leaks
        ~WindowsMMap() {
            if (mapped_data){
                UnmapViewOfFile(mapped_data);
            }
            if (hMapping){
                CloseHandle(hMapping);
            }
            if (hFile != INVALID_HANDLE_VALUE){
                CloseHandle(hFile);
            }
        }
        std::string_view get_view() const { 
            return { static_cast<const char*> (mapped_data), file_size }; 
        }
};

//tokenizer class
class GPT4Tokenizer {
    private:
        int byte_map[256];
        std::unordered_map<uint64_t, int> merges;
        std::unordered_map<std::string, int> special_tokens;
        pcre2_code* re = nullptr;

        inline uint64_t pack_pair(int left, int right) const {
            return (static_cast<uint64_t> (left) << 32) | static_cast<uint32_t> (right);
        }

        //bpe implementation (O(n^2))
        std::vector<int> bpe_internal(std::string_view chunk, std::vector<int>& ids_buf) const {
            ids_buf.clear();
            for (unsigned char b : chunk){
                ids_buf.push_back(byte_map[b]);
            }

            while (ids_buf.size() >= 2) {
                int best_rank = INT_MAX, best_idx = -1, best_new_id = -1;
                for (int i = 0; i < (int) ids_buf.size() - 1; ++i) {
                    auto it = merges.find(pack_pair(ids_buf[i], ids_buf[i+1]));
                    if (it != merges.end() && it->second < best_rank) {
                        best_rank = it->second; 
                        best_idx = i; 
                        best_new_id = it->second;
                    }
                }

                if (best_idx == -1){
                    break;
                }

                ids_buf[best_idx] = best_new_id;
                ids_buf.erase(ids_buf.begin() + best_idx + 1);
            }
            return ids_buf;
        }

    public:
        GPT4Tokenizer(const std::string& vocab_file, const std::string& special_file) {

            std::ifstream file(vocab_file);
            if (!file.is_open()){
                throw std::runtime_error("Vocab file missing.");
            }
            std::string line; bool parsing_merges = false;
            merges.reserve(100000);
            while (std::getline(file, line)) {
                if (line == "[BYTE_MAP]"){
                    parsing_merges = false; 
                    continue; 
                }
                if (line == "[MERGES]"){ 
                    parsing_merges = true; 
                    continue; 
                }
                if (!parsing_merges) {
                    int b, id; 
                    if (sscanf_s(line.c_str(), "%d %d", &b, &id) == 2){
                        byte_map[b] = id;
                    } 
                } else {
                    int l, r, n; 
                    if (sscanf_s(line.c_str(), "%d %d %d", &l, &r, &n) == 3){
                        merges[pack_pair(l, r)] = n;
                    }
                }
            }

            //load special tokens
            std::string special_pattern;
            std::ifstream s_file(special_file);

            if (s_file.is_open()) {
                std::string s_token; 
                int s_id;
                while (s_file >> s_token >> s_id) {
                    special_tokens[s_token] = s_id;
                    if (!special_pattern.empty()){
                        special_pattern = special_pattern + "|";
                    }
                    special_pattern = special_pattern + escape_regex(s_token);
                }
            }

            std::string main_p = R"((?i:'s|'t|'re|'ve|'m|'ll|'d)|[^\r\n\p{L}\p{N}]?\p{L}+|\p{N}{1,3}| ?[^\s\p{L}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+)";
            std::string final_p;
            if (special_pattern.empty()) {
                final_p = main_p;
            } else {
                final_p = "(" + special_pattern + ")|" + main_p;
            }

            int err; 
            PCRE2_SIZE erroff;
            re = pcre2_compile((PCRE2_SPTR)final_p.c_str(), PCRE2_ZERO_TERMINATED, PCRE2_UTF | PCRE2_UCP, &err, &erroff, NULL);
            pcre2_jit_compile(re, PCRE2_JIT_COMPLETE);
        }

        //free resources
        ~GPT4Tokenizer(){ 
            pcre2_code_free(re);
        }

        //thread worker function
        void thread_worker(std::string_view slice, std::string* out_buffer) const {
            //thread local resources
            pcre2_match_data* match_data = pcre2_match_data_create_from_pattern(re, NULL);
            std::unordered_map<std::string, std::vector<int>> local_cache;
            local_cache.reserve(CACHE_SIZE);
            std::vector<int> reuse_vec; 
            char int_buf[20];

            PCRE2_SPTR subject = (PCRE2_SPTR)slice.data();
            PCRE2_SIZE len = slice.length(), offset = 0;
            PCRE2_SIZE* ovector = pcre2_get_ovector_pointer(match_data);

            while (offset < len && pcre2_jit_match(re, subject, len, offset, 0, match_data, NULL) >= 0) {
                std::string_view chunk_view(slice.data() + ovector[0], ovector[1] - ovector[0]);
                std::string chunk(chunk_view);
                
                //check for special tokens first
                auto spec_it = special_tokens.find(chunk);
                if (spec_it != special_tokens.end()) {
                    auto [ptr, ec] = std::to_chars(int_buf, int_buf + 20, spec_it->second);
                    out_buffer->append(int_buf, ptr - int_buf);
                    out_buffer->push_back(' ');
                } else {
                    //cached BPE logic
                    std::vector<int> tokens;
                    if (chunk.size() <= 2) {
                        tokens = bpe_internal(chunk_view, reuse_vec);
                    } else {
                        auto it = local_cache.find(chunk);
                        if (it != local_cache.end()){
                            tokens = it->second;
                        }
                        else tokens = local_cache[chunk] = bpe_internal(chunk_view, reuse_vec);
                    }

                    for (int id : tokens) {
                        auto [ptr, ec] = std::to_chars(int_buf, int_buf + 20, id);
                        out_buffer->append(int_buf, ptr - int_buf);
                        out_buffer->push_back(' ');
                    }
                }
                offset = ovector[1];
                if (local_cache.size() > CACHE_SIZE_MAX){
                    local_cache.clear();
                }
            }
            pcre2_match_data_free(match_data);
        }
};


//main entrypoint, also handles thread management
int main(int argc, char* argv[]) {
    
    std::string map_file = "gpt4_tokenizer_data.txt", special_file = "special.txt", input_file = "", output_file = "";
    int thread_count = 0; // 0 = Auto

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "-i" && i + 1 < argc){
            input_file = argv[++i];
        } else if (arg == "-o" && i + 1 < argc){
            output_file = argv[++i];
        } else if (arg == "-m" && i + 1 < argc){
            map_file = argv[++i];
        } else if (arg == "-s" && i + 1 < argc){
            special_file = argv[++i];
        }
        else if (arg == "-t" && i + 1 < argc){
            thread_count = std::stoi(argv[++i]);
        }
    }

    if (input_file.empty()){
        return 1;
    }

    try {
        GPT4Tokenizer tokenizer(map_file, special_file);
        WindowsMMap mmap(input_file);
        std::string_view full_view = mmap.get_view();

        //thread selection logic
        if (thread_count <= 0){
            size_t size_mb = full_view.size() / (1024 * 1024);
            if (size_mb < 1){
                thread_count = 1;
            }
            else if (size_mb < 10) {
                thread_count = 4;
            }
            else{
                thread_count = std::thread::hardware_concurrency();
            }
        }

        std::cerr << "Using " << thread_count << " threads.\n";

        //divide work into safe slices by splitting at newlines
        std::vector<std::string_view> slices;
        size_t last_pos = 0;
        for (int i = 1; i <= thread_count; ++i) {
            size_t target = (full_view.size() / thread_count) * i;
            while (target < full_view.size() && full_view[target] != '\n'){
                target++;
            }
        
            // consume the entire newline run into the current slice
            while (target < full_view.size() && (full_view[target] == '\n' || full_view[target] == '\r')){
                target++;
            } 
            slices.push_back(full_view.substr(last_pos, target - last_pos));
            last_pos = target;
        }

        std::vector<std::string> results(thread_count);
        std::vector<std::thread> workers;

        auto start = std::chrono::high_resolution_clock::now();

        for (int i = 0; i < thread_count; ++i) {
            workers.emplace_back(&GPT4Tokenizer::thread_worker, &tokenizer, slices[i], &results[i]);
        }

        for (auto& t : workers){
            t.join();
        }

        //sequential write to disk to prevent thrashing or race conditions
        std::ofstream out(output_file.empty() ? "NUL" : output_file, std::ios::binary);
        for (const auto& s : results){
            out.write(s.data(), s.size());
        }

        auto end = std::chrono::high_resolution_clock::now();
        std::cerr << "Finished in " << std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count() << "ms\n";

    } catch (const std::exception& e) { 
        std::cerr << e.what() << "\n"; 
    }
    
    return 0;
}