#!/usr/bin/env python3
import os
import sys



def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    # Ensure local packages are importable
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from diagnostics.diagnostics import load_config, check_llama, run_prompt

    cfg = load_config(project_root)

    llama_cli = cfg["llama_cpp_path"]
    default_model = cfg["model_path"]

    # Candidate three models to check
    candidates = [
        default_model,
        os.path.join(project_root, "model", "openhermes-2.5-mistral-7b.Q4_K_M.gguf"),
        os.path.join(project_root, "model", "mythomax-l2-13b.Q4_K_M.gguf"),
    ]

    # Ensure llama-cli is reachable
    check_llama(llama_cli)

    # Use per-model template to improve generation fidelity
    prompt = "Say hello politely."
    def infer_model_type(model_path: str) -> str:
        name = os.path.basename(model_path).lower()
        # OpenHermes 2.x is trained for ChatML-style prompting; use manual ChatML string
        if "openhermes" in name or "hermes" in name:
            return "chatml-manual"
        # Default to raw prompting (-no-cnv)
        return "raw"
    print(f"[info] Running quick diagnostics on {len(candidates)} model(s) …")
    for mp in candidates:
        if not os.path.exists(mp):
            print(f"[skip] model not found: {mp}")
            continue
        print(f"\n=== {os.path.basename(mp)} ===")
        try:
            mt = infer_model_type(mp)
            rc = run_prompt(llama_cli, mp, model_type=mt, prompt=prompt, n=64)
            if rc != 0:
                print(f"[warn] non-zero exit code: {rc}")
            else:
                print(f"[pass] {os.path.basename(mp)} diagnostics passed")
        except Exception as e:
            print(f"[error] {e}")


if __name__ == "__main__":
    main()
