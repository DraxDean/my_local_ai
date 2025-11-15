
# my_local_ai
Local AI scaffold (Hybrid memory: Mistral for summaries, small model for embeddings)

## Quickstart (macOS, M1)
1. Unzip project and move to `~/Documents/my_local_ai` (or a path you prefer).
2. Install prerequisites:
   - Install llama.cpp CLI (see https://github.com/ggerganov/llama.cpp) and ensure `llama` is in your PATH.
   - Python deps: `pip install sentence-transformers faiss-cpu numpy`
3. Download the Mistral model into `model/`:
   `curl -L -o model/Mistral-Nemo-Base-12B.Q4_K_M.gguf https://huggingface.co/mistralai/Mistral-Nemo-Base-12B-GGUF/resolve/main/Mistral-Nemo-Base-12B.Q4_K_M.gguf`
4. Populate `notes/` with .txt or .md files.
5. Run memory build:
   `python scripts/update_memory.py`
6. Start assistant:
   `python scripts/run_llm.py`

Notes:
 - The scripts call the llama.cpp CLI for summaries and generation; you can edit config.json to point to a different CLI binary if needed.
 - If you don't have faiss-cpu, the scripts will save raw vectors as a fallback.
 - These scripts are intentionally simple and clear; you can replace the llama CLI calls with direct python bindings if you prefer.
