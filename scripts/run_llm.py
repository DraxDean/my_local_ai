#!/usr/bin/env python3
import os
import json
import subprocess
import sys
import time
import signal

# === SILENCE DEBUG ===
os.environ["GGML_METAL_DEBUG"] = "0"
os.environ["GGML_DEBUG"] = "0"

# === LOAD CONFIG ===
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
config_path = os.path.join(project_root, "config.json")

if not os.path.exists(config_path):
    print(f"[ERROR] config.json not found: {config_path}")
    sys.exit(1)

with open(config_path, "r") as f:
    config = json.load(f)

model_path = config["model_path"]
llama_cli = config["llama_cpp_path"]

if not os.path.exists(model_path):
    print(f"[ERROR] Model missing: {model_path}")
    sys.exit(1)
if not os.path.isfile(llama_cli):
    print(f"[ERROR] llama-cli missing: {llama_cli}")
    sys.exit(1)

# === CLI COMMAND ===
cmd = [
    llama_cli,
    "--model", model_path,
    "--n-gpu-layers", "999",
    "--ctx-size", "4096",
    "--temp", "0.7",
    "--top-k", "40",
    "--top-p", "0.95",
    "--repeat-penalty", "1.1",
    "--no-warmup",
    "--color"
]

print("Local AI ready. Type your message (Ctrl-C to quit).")
print("You: ", end="", flush=True)

def signal_handler(sig, frame):
    print("\nShutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# === MAIN LOOP ===
while True:
    try:
        user_input = sys.stdin.readline()
        
        if not user_input:
            break
            
        if user_input.strip().lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        prompt = user_input.strip()
        if prompt:
            # Format prompt for Mistral/Nemo instruct model
            full_prompt = f"[INST] {prompt} [/INST]"
            
            try:
                # Run inference
                proc = subprocess.Popen(
                    cmd + ["--prompt", full_prompt],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True
                )
                
                print("AI: ", end="", flush=True)
                for line in proc.stdout:
                    if line.strip():
                        print(line, end="", flush=True)
                proc.wait()
                print("\nYou: ", end="", flush=True)
                
            except Exception as e:
                print(f"\n[ERROR] {e}")
                time.sleep(2)

    except KeyboardInterrupt:
        print("\nShutting down...")
        break
    except Exception as e:
        print(f"\n[ERROR] {e}")
        time.sleep(3)