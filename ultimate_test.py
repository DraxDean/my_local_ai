#!/usr/bin/env python3
import json
import subprocess
import sys

print("=== COMPLETE RAW MODE TEST ===")

# Load config
with open("config.json") as f:
    config = json.load(f)

llama_cli = config["llama_cpp_path"] 
model_path = config["model_path"]

# Test 1: Simple diagnostic style
print("\\n1. DIAGNOSTIC STYLE TEST:")
cmd1 = [
    llama_cli,
    "--model", model_path,
    "--n-gpu-layers", "999", 
    "--temp", "0.7",
    "-p", "You are Kara, a warrior spirit. Say fuck.",
    "-n", "50",
    "--no-display-prompt",
    "--log-disable"
]

try:
    result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=30)
    print(f"Response: '{result1.stdout.strip()}'")
    print(f"Return code: {result1.returncode}")
    if result1.stderr:
        print(f"Stderr: {result1.stderr[:100]}...")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Even simpler
print("\\n2. ULTRA SIMPLE TEST:")
cmd2 = [
    llama_cli,
    "--model", model_path,
    "-p", "Say fuck",
    "-n", "10",
    "--no-display-prompt",
    "--log-disable"
]

try:
    result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=30)
    print(f"Response: '{result2.stdout.strip()}'")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Check what the main script config thinks
print(f"\\n3. CONFIG CHECK:")
print(f"Model: {model_path}")
print(f"Model type: {config.get('model_type', 'not set')}")

print("\\n=== END TEST ===")