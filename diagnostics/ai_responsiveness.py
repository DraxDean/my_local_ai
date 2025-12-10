
import subprocess
import json
import sys
import time
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '../config.json')

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def run_llama_cli(prompt, timeout=30):
    config = load_config()
    llama_path = config['llama_cpp_path']
    model_path = config['model_path']
    try:
        proc = subprocess.Popen(
            [llama_path, '--model', model_path, '--log-disable', '--prompt', prompt, '--n-predict', '64'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            return None, 'Timeout expired'
        return out, err
    except Exception as e:
        return None, str(e)

def main():
    test_prompt = "Hello! Please reply with any text."
    print(f"[Diagnostics] Sending prompt: {test_prompt}")
    out, err = run_llama_cli(test_prompt)
    if out and out.strip():
        print("[Diagnostics] AI responded:")
        print(out.strip())
        sys.exit(0)
    else:
        print("[Diagnostics] No response or error:")
        print(err)
        sys.exit(1)

if __name__ == "__main__":
    main()
