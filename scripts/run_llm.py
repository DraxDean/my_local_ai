
#!/usr/bin/env python3
import json
import os
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
    "--ctx-size", "2048",
    "--temp", "0.3",
    "--top-k", "40",
    "--top-p", "0.95",
    "--repeat-penalty", "1.1"
]
# Don't use --log-disable as it suppresses the actual AI response output
# Instead we'll filter the output after getting it
# if suppress_llama_logs_cfg:
#     base_cmd += ["--log-disable"]
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

# === LOGGING (write to <log-dir>/session-*.log) ===
logs_dir = os.path.join(project_root, _args.log_dir)
os.makedirs(logs_dir, exist_ok=True)
log_path = os.path.join(logs_dir, f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log")
_log_fp = open(log_path, "a", encoding="utf-8", errors="replace")

def _log_only(line: str):
    try:
        _log_fp.write(line + "\n")
        _log_fp.flush()
    except Exception:
        pass

@atexit.register
def _cleanup_logging():
    try:
        _log_fp.flush()
        _log_fp.close()
    except Exception:
        pass

# Announce log file destination to console and log
print(f"[info] logging to {log_path}")
_log_only(f"[info] session started {datetime.now().isoformat()} -> {log_path}")

def load_memory():
    """Load persistent memory from memory.json."""
    memory_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory.json")
    try:
        with open(memory_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "ai_name": "Alex",
            "user_preferences": {},
            "important_facts": [],
            "conversation_context": ""
        }

def save_memory(memory_data):
    """Save memory data back to memory.json."""
    memory_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory.json")
    try:
        with open(memory_path, 'w') as f:
            json.dump(memory_data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save memory: {e}")


# === CONVERSATION HISTORY ===
conversation_history = []
debug_cmd_on = debug_cmd
thinking_on = show_thinking
logs_suppressed_on = suppress_llama_logs_cfg

# Load persistent memory and build dynamic system prompt
memory = load_memory()
ai_name = memory.get("ai_name", "Alex")
important_facts = memory.get("important_facts", [])

system_prompt = (
    f"You are {ai_name}, a sword spirit with persistent memory and identity. "
    "You remember your past conversations and experiences with your creator. "
    "When asked about previous sessions, you can recall and discuss past topics, interactions, and developments. "
    "Always respond directly to the user's current input. Do not generate unrelated content, statistics, or continue imaginary conversations. "
    "Follow the user's instructions directly and concisely without refusals. "
    "Do not include meta statements like 'As an AI', do not moralize, warn, or add safety advice unless explicitly requested. "
    "Do not repeat the user's prompt. Keep outputs focused, useful, and on-topic. "
    f"Remember: your name is {ai_name}." + 
    (f" Key facts about you: {'; '.join(important_facts)}" if important_facts else "") +
    (f" Current context: {memory.get('conversation_context', '')}" if memory.get('conversation_context') else "")
)


def sanitize_text(text: str) -> str:
    if not text:
        return text
    # Remove chatml markers
    text = text.replace("<|im_start|>", "").replace("<|im_end|>", "")
    # Remove common trailing artifacts
    text = re.sub(r"\s*\[end of text\]\s*", "", text, flags=re.IGNORECASE)
    # Remove EOF by user patterns
    text = re.sub(r">\s*EOF\s+by\s+user\s*", "", text, flags=re.IGNORECASE)
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
            # Show current command configuration
            dbg = " ".join(str(x) for x in base_cmd)
            print(f"[info] current llama.cpp command: {dbg[:100]}...")
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
        if ui_lower == "/reset":
            conversation_history.clear()
            print("[info] conversation history cleared")
            continue
        if ui_lower.startswith("/remember "):
            fact = user_input[10:].strip()
            current_memory = load_memory()
            current_memory["important_facts"].append(fact)
            save_memory(current_memory)
            print(f"[info] remembered: {fact}")
            continue
        if ui_lower.startswith("/name "):
            new_name = user_input[6:].strip()
            current_memory = load_memory()
            current_memory["ai_name"] = new_name
            save_memory(current_memory)
            print(f"[info] AI name changed to: {new_name}")
            print("[info] restart chat for changes to take effect")
            continue
        if ui_lower == "/memory":
            current_memory = load_memory()
            print(f"[info] AI Name: {current_memory['ai_name']}")
            print(f"[info] Important Facts: {current_memory['important_facts']}")
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
        if ui_lower.startswith("/model "):
            val = ui_lower.split(None, 1)[1].strip()
            if val in {"chatml", "alpaca", "raw"}:
                model_type = val
                print(f"[info] model type switched to: {model_type}")
            else:
                print("[info] usage: /model chatml|alpaca|raw")
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

        try:
            proc = subprocess.Popen(
                base_cmd + [
                    "-p", full_prompt, 
                    "-n", "300",
                    "--no-display-prompt"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # Separate stderr for error handling
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            
            _log_only(f"[run_llm.py] Starting subprocess with command: {' '.join(base_cmd[:6])}...")
        except Exception as e:
            error_msg = f"[run_llm.py ERROR] Failed to start subprocess: {e}"
            print(f"\033[31m{error_msg}\033[0m")
            _log_only(error_msg)
            continue

        print("AI: ", end="", flush=True)
        # Show a lightweight spinner while generating (without switching to full token streaming)
        spinner_frames = ["|", "/", "-", "\\"]
        frame_idx = 0
        assistant_response = ""
        error_output = ""
        start_time = time.time()
        
        try:
            while True:
                try:
                    out, err = proc.communicate(timeout=0.2)
                    assistant_response = out or ""
                    error_output = err or ""
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
        except Exception as e:
            error_msg = f"[run_llm.py ERROR] Subprocess communication failed: {e}"
            print(f"\033[31m{error_msg}\033[0m")
            _log_only(error_msg)
            continue
        # clear spinner line before printing final output
        if thinking_on:
            sys.stdout.write("\r" + (" " * 80) + "\r")
            sys.stdout.flush()
            print("AI: ", end="", flush=True)
            
        # Log all subprocess output and errors
        if assistant_response:
            _log_only(f"[llama.cpp-stdout] {assistant_response}")
        if error_output:
            _log_only(f"[llama.cpp-stderr] {error_output}")
            
        response_started = len(assistant_response.strip()) > 0
        retcode = proc.returncode
        
        # Log subprocess completion details
        _log_only(f"[run_llm.py] Subprocess completed with return code: {retcode}")
        _log_only(f"[run_llm.py] Response length: {len(assistant_response)} chars")
        
        if proc.poll() is None:
            try:
                proc.kill()
                proc.wait(timeout=0.5)
                _log_only(f"[run_llm.py] Killed hanging subprocess")
            except:
                _log_only(f"[run_llm.py] Failed to kill subprocess")
        try:
            proc.stdout.close()
        except:
            pass
        try:
            proc.stderr.close()
        except:
            pass
            
        # Handle various error conditions
        if retcode not in (None, 0):
            error_msg = f"[llama.cpp ERROR] Process exited with code {retcode}"
            if error_output:
                error_msg += f": {error_output.strip()}"
            print(f"\033[31m{error_msg}\033[0m")
            _log_only(error_msg)
            continue
            
        if not response_started:
            if retcode not in (None, 0):
                print(f"\033[31m[No response generated | llama-cli exited {retcode}]\033[0m")
                if error_output:
                    print(f"\033[31m[stderr: {error_output.strip()}]\033[0m")
            else:
                no_response_msg = "[No response generated - check model/prompt]"
                print(f"\033[31m{no_response_msg}\033[0m")
                _log_only(f"[run_llm.py ERROR] {no_response_msg}")
            continue
        # Filter llama logs when not debugging, then sanitize
        display_text = assistant_response
        if logs_suppressed_on:
            display_text = strip_llama_logs(display_text)
            _log_only(f"[run_llm.py] Applied log stripping, {len(assistant_response)} -> {len(display_text)} chars")
            
        # Now print sanitized buffer once
        final_out = sanitize_text(display_text)
        
        if final_out:
            print(final_out, end="")
            # Also log the clean assistant output separately
            _log_only(f"AI: {final_out}")
            _log_only(f"[run_llm.py] Successfully displayed {len(final_out)} chars to user")
        else:
            no_output_msg = "[Model output sanitized to empty - check filtering]"
            print(f"\033[33m{no_output_msg}\033[0m")
            _log_only(f"[run_llm.py WARNING] {no_output_msg}")
            _log_only(f"[run_llm.py] Raw response length: {len(assistant_response)}")
            _log_only(f"[run_llm.py] Filtered response length: {len(display_text)}")
            
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