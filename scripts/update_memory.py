#!/usr/bin/env python3
import os, json, subprocess, hashlib
from pathlib import Path

# Project root
BASE = Path(__file__).resolve().parents[1]

# Config
with open(BASE / "config.json", "r") as f:
    cfg = json.load(f)

# Paths
NOTES_DIR = BASE / "notes"
SUMMARIES_PATH = BASE / cfg.get("summaries_path", "memory/summaries.json")
EMBEDDINGS_NPY = BASE / cfg.get("embeddings_npy", "memory/embeddings.npy")
FAISS_INDEX = BASE / cfg.get("faiss_index", "memory/faiss.index")
CHUNK_SIZE = int(cfg.get("chunk_size_chars", 3000))
CHUNK_OVERLAP = int(cfg.get("chunk_overlap_chars", 300))
LLAMA_CMD = cfg.get("llama_cli", "llama")
MODEL_PATH = BASE / cfg.get("model_path", "model/Mistral-Nemo-Base-12B.Q4_K_M.gguf")

# ----------------------------
# Helpers
# ----------------------------
def list_note_files():
    exts = [".txt", ".md", ".markdown"]
    return sorted([p for p in NOTES_DIR.glob("*") if p.suffix.lower() in exts])

def read_text(p): 
    return p.read_text(encoding="utf-8", errors="ignore")

def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks, i, L = [], 0, len(text)
    while i < L:
        end = i + size
        chunks.append(text[i:end].strip())
        i = end - overlap
    return chunks

def llama_summarize(text_chunk):
    prompt = f"Summarize the following text into 1-2 short bullet sentences (keep it factual):\n\n{text_chunk}\n\nSummary:"
    try:
        cmd = f'printf "%s" {json.dumps(prompt)} | {LLAMA_CMD} -m {str(MODEL_PATH)} --n_predict 256 --temp 0.2'
        p = subprocess.run(["bash","-lc", cmd], capture_output=True, text=True, timeout=120)
        if p.returncode == 0 and p.stdout:
            lines = [l.strip() for l in p.stdout.splitlines() if l.strip()]
            return " ".join(lines[:2])
        else:
            print("llama CLI failed or produced no output. stderr:", p.stderr[:400])
            return ""
    except Exception as e:
        print("Error calling llama CLI for summarization:", e)
        return ""

def try_imports():
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
        return np, SentenceTransformer
    except Exception as e:
        print("Missing python packages: sentence-transformers, faiss-cpu, numpy")
        raise

# ----------------------------
# Build memory
# ----------------------------
def build_memory():
    files = list_note_files()
    if not files:
        print("No note files found in notes/. Add some .txt or .md files and re-run.")
        return

    np, SentenceTransformer = try_imports()
    embedder = SentenceTransformer(cfg.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"))

    summaries, vectors = [], []

    for p in files:
        text = read_text(p)
        chunks = chunk_text(text)
        for i, c in enumerate(chunks):
            chunk_id = hashlib.sha256((p.name + str(i)).encode()).hexdigest()[:12]
            print(f"Summarizing chunk {p.name}#{i} (chars={len(c)})...")
            summary = llama_summarize(c) or c[:200].replace("\n"," ").strip()
            summaries.append({"id": chunk_id, "source": p.name, "summary": summary, "length": len(c)})
            vectors.append(embedder.encode(summary))
