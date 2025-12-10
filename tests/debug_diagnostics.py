#!/usr/bin/env python3
"""
Debug diagnostics runner for verbose llama.cpp output and testing.
Saves debug output to tests/ directory and shows full llama.cpp logs.
"""

import os
import sys
import subprocess
import json
from datetime import datetime

# Get project root and config
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
config_path = os.path.join(project_root, "config.json")

with open(config_path, "r") as f:
    config = json.load(f)

llama_cli = config["llama_cpp_path"]
model_path = config["model_path"]

def run_debug_test(prompt: str, output_file: str = None):
    """Run a single prompt with full debug output"""
    
    # Build command with NO log suppression for debug visibility
    cmd = [
        llama_cli,
        "--model", model_path,
        "--ctx-size", "4096",
        "--n-gpu-layers", "999", 
        "--temp", "0.7",
        "--top-k", "40",
        "--top-p", "0.95",
        "--repeat-penalty", "1.1",
        "-no-cnv",  # Raw mode for Dolphin
        "-p", prompt,
        "-n", "100",
        "--no-display-prompt"
    ]
    
    print(f"[debug-run] {' '.join(cmd[:6])} ... -p \"{prompt[:30]}...\"")
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60
        )
        
        output = result.stdout or ""
        
        # Save to file if specified
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"=== Debug Test: {datetime.now().isoformat()} ===\n")
                f.write(f"Command: {' '.join(cmd)}\n")
                f.write(f"Return code: {result.returncode}\n")
                f.write("=== Full Output ===\n")
                f.write(output)
            print(f"[debug-save] Output saved to {output_file}")
        
        # Extract just the AI response (after all the setup logs)
        lines = output.splitlines()
        ai_response = []
        capturing = False
        
        for line in lines:
            # Look for the actual response after generate: line
            if line.strip().startswith("generate: n_ctx"):
                capturing = True
                continue
            elif capturing and not line.strip().startswith(("llama_perf", "llama_memory", "ggml_metal")):
                if line.strip():
                    ai_response.append(line)
        
        clean_response = "\n".join(ai_response).strip()
        
        print(f"[ai-response] {clean_response[:100]}{'...' if len(clean_response) > 100 else ''}")
        print(f"[debug-status] Exit code: {result.returncode}")
        
        return result.returncode == 0, clean_response
        
    except subprocess.TimeoutExpired:
        print("[debug-error] Command timed out after 60s")
        return False, ""
    except Exception as e:
        print(f"[debug-error] {e}")
        return False, ""

def main():
    print("=== Debug Diagnostics Runner ===")
    
    # Create tests output directory
    tests_dir = os.path.join(project_root, "tests")
    os.makedirs(tests_dir, exist_ok=True)
    
    # Test prompts
    test_prompts = [
        "Say hello politely.",
        "What is 2 + 2?",
        "Explain quantum computing in one sentence."
    ]
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n--- Debug Test {i}/{len(test_prompts)} ---")
        output_file = os.path.join(tests_dir, f"debug-test-{timestamp}-{i}.log")
        
        success, response = run_debug_test(prompt, output_file)
        
        if success:
            print(f"[pass] Test {i} completed")
        else:
            print(f"[fail] Test {i} failed")
    
    print(f"\n[debug-summary] Tests completed. Debug logs in {tests_dir}/")

if __name__ == "__main__":
    main()