#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys


def load_config(project_root: str):
    cfg_path = os.path.join(project_root, "config.json")
    if not os.path.exists(cfg_path):
        print(f"[ERROR] config.json not found at {cfg_path}")
        sys.exit(1)
    with open(cfg_path, "r") as f:
        return json.load(f)


def build_base_cmd(llama_cli: str, model_path: str, model_type: str, ctx: str, n_gpu: str, temp: str):
    cmd = [
        llama_cli,
        "--model", model_path,
        "--ctx-size", ctx,
        "--n-gpu-layers", n_gpu,
        "--temp", temp,
        "--top-k", "40",
        "--top-p", "0.95",
        "--repeat-penalty", "1.1",
    ]
    if model_type == "chatml":
        cmd += ["--chat-template", "chatml"]
    else:
        cmd += ["-no-cnv"]
    return cmd


def run_cmd(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            cmd,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.STDOUT,
        )
    except FileNotFoundError:
        print(f"[ERROR] Command not found: {cmd[0]}")
        sys.exit(1)


def check_llama(llama_cli: str):
    print("[check] llama.cpp binary reachable …", end=" ")
    res = run_cmd([llama_cli, "--help"]) 
    if res.returncode == 0 and res.stdout:
        print("ok")
    else:
        print("fail")
        print(res.stdout)
        sys.exit(1)


def check_model_load(llama_cli: str, model_path: str, model_type: str):
    print(f"[check] model loads: {os.path.basename(model_path)} …", end=" ")
    base = build_base_cmd(llama_cli, model_path, model_type, ctx="1024", n_gpu="999", temp="0.7")
    test = base + ["-p", "hello", "-n", "16", "--no-display-prompt"]
    res = run_cmd(test)
    if res.returncode == 0:
        print("ok")
    else:
        print("fail")
        print(res.stdout)
        sys.exit(1)


def _build_chatml_prompt(user_text: str) -> str:
    return (
        "<|im_start|>system\nYou are a helpful, direct assistant.\n<|im_end|>\n"
        "<|im_start|>user\n" + user_text + "\n<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


def run_prompt(llama_cli: str, model_path: str, model_type: str, prompt: str, n: int):
    # For "chatml-manual", we send a ChatML-formatted string and force -no-cnv
    effective_type = model_type
    effective_prompt = prompt
    if model_type == "chatml-manual":
        effective_type = "raw"
        effective_prompt = _build_chatml_prompt(prompt)

    base = build_base_cmd(llama_cli, model_path, effective_type, ctx="4096", n_gpu="999", temp="0.7")
    cmd = base + ["-p", effective_prompt, "-n", str(n), "--no-display-prompt"]
    print("[run] ", " ".join(cmd[:-1] + ["--no-display-prompt"]))
    res = run_cmd(cmd)
    print("\n[output]\n" + (res.stdout or ""))
    return res.returncode


def detect_models(project_root: str):
    model_dir = os.path.join(project_root, "model")
    if not os.path.isdir(model_dir):
        return []
    return [os.path.join(model_dir, f) for f in os.listdir(model_dir) if f.endswith('.gguf')]


def load_prompts_file(path: str):
    prompts = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith('#'):
                continue
            prompts.append(s)
    return prompts


def main():
    parser = argparse.ArgumentParser(description="Local AI diagnostics for llama.cpp + GGUF models")
    parser.add_argument("--prompt", help="Prompt to run (safe diagnostics)", default=None)
    parser.add_argument("--n", help="Max tokens to generate", default="64")
    parser.add_argument("--model", help="Override model path", default=None)
    parser.add_argument("--setup-test", action="store_true", help="Run quick setup checks (binary + model load)")
    parser.add_argument("--prompts-file", help="File with prompts (one per line, # for comments)", default=None)
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    cfg = load_config(project_root)

    llama_cli = cfg["llama_cpp_path"]
    model_path = args.model or cfg["model_path"]
    model_type = cfg.get("model_type", "chatml")

    check_llama(llama_cli)
    if args.setup_test:
        check_model_load(llama_cli, model_path, model_type)
        print("[info] Setup checks passed.")

    if args.prompts_file:
        prompts = load_prompts_file(args.prompts_file)
        if not prompts:
            print(f"[warn] No prompts found in {args.prompts_file}")
            sys.exit(0)
        for i, p in enumerate(prompts, 1):
            print(f"\n--- Prompt {i}/{len(prompts)} ---\n{p}")
            rc = run_prompt(llama_cli, model_path, model_type, p, int(args.n))
            if rc == 0:
                print(f"[pass] Prompt {i} completed successfully")
            else:
                print(f"[fail] Prompt {i} exited with code {rc}")
                # Continue to next prompt rather than exiting; summary at end
        print(f"[pass] All {len(prompts)} prompts processed")
        sys.exit(0)
    elif args.prompt:
        rc = run_prompt(llama_cli, model_path, model_type, args.prompt, int(args.n))
        if rc == 0:
            print("[pass] Single-prompt diagnostics passed")
        sys.exit(rc)
    else:
        # If no prompt given, offer a quick benign test
        print("[info] No prompt provided. Running benign prompt: 'Say hello politely.'")
        rc = run_prompt(llama_cli, model_path, model_type, "Say hello politely.", 64)
        if rc == 0:
            print("[pass] Benign prompt diagnostics passed")


if __name__ == "__main__":
    main()
