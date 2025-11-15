#!/usr/bin/env python3
import subprocess
import os
from pathlib import Path

# Project root
BASE = Path(__file__).resolve().parents[1]

# Model path (relative to project)
MODEL_PATH = BASE / "model" / "Mistral-Nemo-Base-12B.Q4_K_M.gguf"

# Check model exists
if not MODEL_PATH.exists():
    print(f"Error: Model not found at {MODEL_PATH}")
    exit(1)

# llama command (relative or full path if symlinked in ~/bin)
LLAMA_CMD = "llama"

print("Local AI with memory. Type your question (Ctrl-C to exit).")

try:
    while True:
        prompt = input("\nYou: ").strip()
        if not prompt:
            continue

        # Build llama CLI command
        cmd = [
            LLAMA_CMD,
            "-m", str(MODEL_PATH),
            "-p", prompt,
            "--n_predict", "256",
            "--temp", "0.2",
            "--color"
        ]

        subprocess.run(cmd)
except KeyboardInterrupt:
    print("\nExiting.")
