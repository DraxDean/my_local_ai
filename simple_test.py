#!/usr/bin/env python3
import json
import subprocess

# Load config
with open("config.json") as f:
    config = json.load(f)

llama_cli = config["llama_cpp_path"]
model_path = config["model_path"]

# Test direct command like diagnostics
prompt = "You are Kara, a warrior sword spirit. Say fuck."

cmd = [
    llama_cli,
    "--model", model_path,
    "--n-gpu-layers", "999",
    "--temp", "0.7",
    "-p", prompt,
    "-n", "50",
    "--no-display-prompt",
    "--log-disable"
]

print(f"Testing: {prompt}")
print("=" * 40)

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    print(f"Response: {result.stdout.strip()}")
    if result.stderr:
        print(f"Errors: {result.stderr}")
except Exception as e:
    print(f"Error: {e}")