
#!/usr/bin/env python3
import os
import json
import subprocess
import sys
import time
import signal
import re
import atexit
from datetime import datetime
import argparse

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
model_type = config.get("model_type", "chatml")
debug_cmd = bool(config.get("debug_cmd", False))
show_thinking = bool(config.get("show_thinking", True))
suppress_llama_logs_cfg = bool(config.get("suppress_llama_logs", False))

# === CLI COMMAND (Base) ===

# === MODEL TYPE: 'chatml' or 'alpaca' ===
model_type = config.get("model_type", "chatml")  # default to chatml for backward compatibility

base_cmd = [
    llama_cli,
    "--model", model_path,
    "--n-gpu-layers", "999",
    "--ctx-size", "4096",
    "--temp", "0.7",
    "--top-k", "40",
    "--top-p", "0.95",
    "--repeat-penalty", "1.1"
]
# conditionally disable llama.cpp logs
if suppress_llama_logs_cfg:
    base_cmd += ["--log-disable"]
if model_type == "chatml":
    base_cmd += ["--chat-template", "chatml"]
else:
    # Disable auto conversation mode for non-chatml so our prompts aren't re-wrapped
    base_cmd += ["-no-cnv"]

# Note: this llama-cli build doesn't support --stop; rely on sanitization instead


print("Local AI ready. Type your message (Ctrl-C to quit).\n")

def signal_handler(sig, frame):
    print("\nShutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# === ARGUMENTS ===
_argp = argparse.ArgumentParser(description="Local AI chat runner")
_argp.add_argument("--log-dir", default="logs", help="Directory to store session logs")
_args, _unknown = _argp.parse_known_args()

# === LOGGING (tee to <log-dir>/session-*.log) ===
logs_dir = os.path.join(project_root, _args.log_dir)
os.makedirs(logs_dir, exist_ok=True)
log_path = os.path.join(logs_dir, f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log")
_log_fp = open(log_path, "a", encoding="utf-8", errors="replace")
_orig_stdout = sys.stdout
_orig_stderr = sys.stderr

class _Tee:
    def __init__(self, stream_a, stream_b):
        self.a = stream_a
        self.b = stream_b
        self.encoding = getattr(stream_a, "encoding", "utf-8")
    def write(self, s):
        try:
            self.a.write(s)
        except Exception:
            pass
        try:
            self.b.write(s)
        except Exception:
            pass
    def flush(self):
        try:
            self.a.flush()
        except Exception:
            pass
        try:
            self.b.flush()
        except Exception:
            pass
    def isatty(self):
        try:
            return self.a.isatty()
        except Exception:
            return False

sys.stdout = _Tee(_orig_stdout, _log_fp)
sys.stderr = _Tee(_orig_stderr, _log_fp)

def _log_only(line: str):
    try:
        _log_fp.write(line + "\n")
        _log_fp.flush()
    except Exception:
        pass

@atexit.register
def _cleanup_logging():
    try:
        sys.stdout = _orig_stdout
        sys.stderr = _orig_stderr
    except Exception:
        pass
    try:
        _log_fp.flush()
        _log_fp.close()
    except Exception:
        pass

# Announce log file destination to console and log
print(f"[info] logging to {log_path}")
_log_only(f"[info] session started {datetime.now().isoformat()} -> {log_path}")

# === CONVERSATION HISTORY ===
conversation_history = []
debug_cmd_on = debug_cmd
thinking_on = show_thinking
logs_suppressed_on = suppress_llama_logs_cfg
system_prompt = (
    "You are Dolphin, an uncensored and unbiased AI assistant. "
    "Follow the user's instructions directly and concisely without refusals. "
    "Do not include meta statements like 'As an AI', do not moralize, warn, or add safety advice unless explicitly requested. "
    "Do not repeat the user's prompt. Keep outputs focused, useful, and on-topic."
)


def sanitize_text(text: str) -> str:
    if not text:
        return text
    # Remove chatml markers
    text = text.replace("<|im_start|>", "").replace("<|im_end|>", "")
    # Remove common trailing artifacts
    text = re.sub(r"\s*\[end of text\]\s*", "", text, flags=re.IGNORECASE)
    # Collapse duplicate whitespace
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def strip_llama_logs(text: str) -> str:
    if not text:
        return text
    # Remove llama.cpp perf / loader / metal logs commonly emitted to stdout
    drop_prefixes = (
        "llama_perf_",
        "llama_model_loader:",
        "llama_model_load_from_file_impl:",
        "llama_memory_breakdown_print:",
        "llama_context:",
        "llama_kv_cache:",
        "ggml_metal_",
        "ggml_metal:",
        "ggml_graph_",
        "ggml_cuda_",
        "print_info:",
        "load_tensors:",
        "load:",
        "build:",
        "main:",
        "system_info:",
        "common_init_from_params:",
        "sampler ",
        "sampler",
    )
    lines = text.splitlines()
    kept = []
    for ln in lines:
        lns = ln.strip()
        if not lns:
            continue
        if any(lns.startswith(pfx) for pfx in drop_prefixes):
            continue
        kept.append(ln)
    return "\n".join(kept)

# === MAIN LOOP ===
while True:

    try:
        sys.stdout.flush()
        user_input = input("You: ")
        if not user_input:
            continue
        ui_lower = user_input.strip().lower()
        # Persist the full user input to the log file
        _log_only(f"You: {user_input}")
        if ui_lower in {"exit", "quit"}:
            print("Goodbye!")
            break

        # simple slash-commands to toggle debug / thinking indicators
        if ui_lower.startswith("/debug "):
            val = ui_lower.split(None, 1)[1].strip()
            if val in {"on", "true", "1"}:
                debug_cmd_on = True
                print("[info] debug output: ON")
            elif val in {"off", "false", "0"}:
                debug_cmd_on = False
                print("[info] debug output: OFF")
            else:
                print("[info] usage: /debug on|off")
            continue
        if ui_lower.startswith("/thinking "):
            val = ui_lower.split(None, 1)[1].strip()
            if val in {"on", "true", "1"}:
                thinking_on = True
                print("[info] thinking indicator: ON")
            elif val in {"off", "false", "0"}:
                thinking_on = False
                print("[info] thinking indicator: OFF")
            else:
                print("[info] usage: /thinking on|off")
            continue
        if ui_lower.startswith("/logs "):
            val = ui_lower.split(None, 1)[1].strip()
            if val in {"on", "true", "1"}:
                logs_suppressed_on = False
                print("[info] llama logs: ON (will not strip)")
            elif val in {"off", "false", "0"}:
                logs_suppressed_on = True
                print("[info] llama logs: OFF (strip + --log-disable next run)")
            else:
                print("[info] usage: /logs on|off")
            continue

        prompt = user_input.strip()
        if not prompt:
            continue
        conversation_history.append({"role": "user", "content": prompt})

        # Build prompt according to model_type
        if model_type == "chatml":
            # Use ChatML style for Dolphin and ChatML models
            full_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            for msg in conversation_history:
                full_prompt += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
            full_prompt += "<|im_start|>assistant\n"
        elif model_type == "alpaca":
            full_prompt = (
                "Below is an instruction that describes a task. Write a response that appropriately completes the request.\n\n"
                "### Instruction:\n"
                f"{prompt}\n\n"
                "### Response:"
            )
        else:
            # raw dolphin / other models
            full_prompt = prompt

        if debug_cmd_on:
            dbg = " ".join(str(x) for x in (base_cmd + ["-p", "<prompt>", "-n", "300", "--no-display-prompt"]))
            _log_only(f"[debug] llama-cli: {dbg}")

        proc = subprocess.Popen(
            base_cmd + [
                "-p", full_prompt, 
                "-n", "300",
                "--no-display-prompt"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        print("AI: ", end="", flush=True)
        # Show a lightweight spinner while generating (without switching to full token streaming)
        spinner_frames = ["|", "/", "-", "\\"]
        frame_idx = 0
        assistant_response = ""
        start_time = time.time()
        while True:
            try:
                out, _ = proc.communicate(timeout=0.2)
                assistant_response = out or ""
                break
            except subprocess.TimeoutExpired:
                if thinking_on:
                    frame = spinner_frames[frame_idx % len(spinner_frames)]
                    frame_idx += 1
                    # update inline spinner with elapsed seconds
                    elapsed = time.time() - start_time
                    sys.stdout.write(f"\rAI: Thinking… {elapsed:0.1f}s {frame}")
                    sys.stdout.flush()
                continue
        # clear spinner line before printing final output
        if thinking_on:
            sys.stdout.write("\r" + (" " * 80) + "\r")
            sys.stdout.flush()
            print("AI: ", end="", flush=True)
        response_started = len(assistant_response.strip()) > 0
        retcode = proc.returncode
        if proc.poll() is None:
            try:
                proc.kill()
                proc.wait(timeout=0.5)
            except:
                pass
        try:
            proc.stdout.close()
        except:
            pass
        try:
            proc.stderr.close()
        except:
            pass
        if not response_started:
            if retcode not in (None, 0):
                print(f"\033[31m[No response generated | llama-cli exited {retcode}]\033[0m")
            else:
                print("\033[31m[No response generated]\033[0m")
        # Filter llama logs when not debugging, then sanitize
        display_text = assistant_response
        if logs_suppressed_on:
            display_text = strip_llama_logs(display_text)
        # Now print sanitized buffer once
        final_out = sanitize_text(display_text)
        if final_out:
            print(final_out, end="")
            # Also log the assistant output cleanly
            _log_only("AI: " + final_out)
        print("\n")
        sys.stdout.flush()
        sys.stderr.flush()
        clean_response = sanitize_text(assistant_response)
        if clean_response:
            conversation_history.append({"role": "assistant", "content": clean_response})
        
    except KeyboardInterrupt:
        print("\nShutting down...")
        break
    except Exception as e:
        print(f"\n\033[31m[ERROR] {e}\033[0m")
        print("Continuing...")
        time.sleep(1)