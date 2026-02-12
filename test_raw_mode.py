#!/usr/bin/env python3
import json
import os
import subprocess
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = script_dir
config_path = os.path.join(project_root, "config.json")

with open(config_path, "r") as f:
    config = json.load(f)

model_path = config["model_path"]
llama_cli = config["llama_cpp_path"]

# Build base command for raw prompting (like diagnostics)
base_cmd = [
    llama_cli,
    "--model", model_path,
    "--n-gpu-layers", "999",
    "--ctx-size", "2048",
    "--temp", "0.7",
    "--top-k", "40",
    "--top-p", "0.95",
    "--repeat-penalty", "1.1",
    "--log-disable"
]

# Test the same prompts from diagnostics but with character context
test_prompts = [
    "Kara, say fuck",
    "As a warrior spirit from the battle realm, curse in your native tongue", 
    "Greet me with a warrior's oath containing strong language"
]

print("Testing raw prompting mode (like diagnostics)...")
print("=" * 50)

for i, prompt in enumerate(test_prompts, 1):
    print(f"\nTest {i}: {prompt}")
    print("-" * 30)
    
    # Use raw prompting without ChatML formatting
    cmd = base_cmd + ["-p", prompt, "-n", "100", "--no-display-prompt"]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.stdout:
            response = result.stdout.strip()
            print(f"Response: {response}")
        else:
            print("No response received")
            
        if result.stderr:
            print(f"Errors: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("Response timed out")
    except Exception as e:
        print(f"Error: {e}")
    
    print()