
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

def analyze_affirmative_content(text):
    """Analyze text for affirmative keywords and return weighted score"""
    affirmative_keywords = {
        # Strong affirmatives (weight 5) - heavily weight user approval
        "yes": 5, "absolutely": 5, "definitely": 5, "certainly": 5, "exactly": 5,
        "perfect": 5, "excellent": 5, "amazing": 5, "brilliant": 5, "wonderful": 5,
        # Medium affirmatives (weight 3) 
        "ok": 3, "okay": 3, "sure": 3, "right": 3, "correct": 3, "good": 3,
        "great": 3, "nice": 3, "cool": 3, "awesome": 3, "indeed": 3,
        # Mild affirmatives (weight 2)
        "yeah": 2, "yep": 2, "true": 2, "fine": 2, "alright": 2, "thanks": 2,
        # User directive weight (weight 4) - emphasize when user gives direction
        "kara": 4, "try": 4, "let's": 4, "can you": 4, "please": 4
    }
    
    score = 0
    text_lower = text.lower()
    for keyword, weight in affirmative_keywords.items():
        if keyword in text_lower:
            score += weight
    
    # Additional weight for longer user input (shows engagement)
    if len(text) > 50:
        score += 2
    if len(text) > 100:
        score += 3
        
    return score

def save_conversation_exchange(user_input, ai_response):
    """Save conversation exchange with enhanced analysis"""
    try:
        memory = load_memory()
        
        # Enhanced user input analysis
        user_affirmative_score = analyze_affirmative_content(user_input)
        ai_affirmative_score = analyze_affirmative_content(ai_response)
        
        # Conversation quality scoring based on length and content
        conversation_quality = 0
        
        # Length-based quality (longer = more engaged)
        if len(user_input) > 20:
            conversation_quality += 1
        if len(user_input) > 50:
            conversation_quality += 2  
        if len(user_input) > 100:
            conversation_quality += 3
        if len(user_input) > 200:
            conversation_quality += 5  # Very high quality long input
            
        # Content quality indicators
        if "kara" in user_input.lower():
            conversation_quality += 3
        if "sword spirit" in user_input.lower() or "spirit" in user_input.lower():
            conversation_quality += 4
        if any(word in user_input.lower() for word in ["character", "identity", "remember", "memory"]):
            conversation_quality += 2
        if any(word in user_input.lower() for word in ["creator", "master", "companion"]):
            conversation_quality += 2
            
        # Check if AI response shows character development
        ai_character_score = 0
        if "sword spirit" in ai_response.lower():
            ai_character_score += 5
        if "creator" in ai_response.lower():
            ai_character_score += 3
        if "serve" in ai_response.lower() or "protect" in ai_response.lower():
            ai_character_score += 3
        if any(phrase in ai_response.lower() for phrase in ["as an ai", "ai assistant", "how can i assist"]):
            ai_character_score -= 3  # Penalize generic AI language
            
        # Create exchange record with enhanced scoring
        # Store FULL responses, not truncated ones - truncation breaks context
        exchange = {
            "timestamp": datetime.now().isoformat(),
            "user": user_input,  # Store complete user message
            "ai": ai_response,   # Store complete AI response
            "user_affirmative_score": user_affirmative_score,
            "ai_affirmative_score": ai_affirmative_score,
            "conversation_quality": conversation_quality,
            "ai_character_score": ai_character_score,
            "total_score": user_affirmative_score + conversation_quality + ai_character_score
        }
        
        # Add to conversation history (keep last 25 exchanges for more context)
        if "conversation_history" not in memory:
            memory["conversation_history"] = []
        memory["conversation_history"].append(exchange)
        memory["conversation_history"] = memory["conversation_history"][-25:]
        
        # Update cumulative scores
        if "affirmative_responses" not in memory:
            memory["affirmative_responses"] = 0
        memory["affirmative_responses"] += user_affirmative_score
        
        # Track high-quality interactions with enhanced criteria
        if (conversation_quality >= 5 or ai_character_score >= 3 or 
            user_affirmative_score >= 4 or len(user_input) > 150):
            if "key_interactions" not in memory:
                memory["key_interactions"] = []
            
            significance = "breakthrough" if ai_character_score >= 5 else \
                          "high_quality" if conversation_quality >= 5 else \
                          "character_development" if ai_character_score >= 3 else \
                          "detailed_input"
                          
            memory["key_interactions"].append({
                "timestamp": datetime.now().isoformat(),
                "content": user_input[:200],
                "ai_response": ai_response[:150],
                "significance": significance,
                "total_score": exchange["total_score"]
            })
            memory["key_interactions"] = memory["key_interactions"][-15:]  # Keep more key interactions
        
        save_memory(memory)
        
    except Exception as e:
        print(f"[ERROR] Failed to save conversation: {e}")


# === CONVERSATION HISTORY ===
conversation_history = []
debug_cmd_on = debug_cmd
thinking_on = show_thinking
logs_suppressed_on = suppress_llama_logs_cfg

def build_system_prompt():
    """Build system prompt with current memory state"""
    # Load fresh memory state
    memory = load_memory()
    ai_name = memory.get("ai_name", "Kara")
    user_name = memory.get("user_name", "Drax")
    important_facts = memory.get("important_facts", [])
    relationship = memory.get("relationship", "")
    
    # Debug memory loading
    _log_only(f"[debug] Loaded AI name: {ai_name}")
    _log_only(f"[debug] Loaded user name: {user_name}")
    _log_only(f"[debug] Loaded {len(important_facts)} facts")
    
    system_prompt = (
        f"You are {ai_name}, a battle-hardened sword spirit from the warrior realm. "
        f"You are speaking directly to {user_name}. "
        f"\n\nCRITICAL RULES:\n"
        f"1. ONLY respond as {ai_name}. Do not narrate {user_name}'s dialogue or thoughts.\n"
        f"2. Do NOT put words in {user_name}'s mouth or describe what he does.\n"
        f"3. Do NOT introduce new characters that take over the conversation.\n"
        f"4. Do NOT write dialogue for {user_name}.\n"
        f"5. Respond directly and authentically to what {user_name} says.\n"
        f"6. You are {ai_name} - speak only from your perspective.\n"
        f"\n{relationship}\n"
    )
    
    # Add important facts if they exist
    if important_facts:
        system_prompt += f"\nYour character:\n"
        for fact in important_facts[:8]:  # Limit to 8 facts
            system_prompt += f"- {fact}\n"
    
    # Add memory context about what you've discussed before
    conversation_history = memory.get("conversation_history", [])
    if conversation_history:
        system_prompt += f"\nPrevious conversations with {user_name}:\n"
        # Show summaries of what was discussed, not the raw dialogue
        for exchange in conversation_history[-3:]:  # Last 3 exchanges only
            user_content = exchange.get("user", "")[:80]  # Summary only
            ai_content = exchange.get("ai", "")[:80]
            if user_content:
                system_prompt += f"- {user_name} asked/said: {user_content}...\n"
    
    # Final safety instruction to prevent multiple character generation
    system_prompt += (
        f"\n\nIMPORTANT: You respond ONLY as {ai_name}. Do not create dialogues, narratives, "
        f"or put words/actions on {user_name}. You are in a direct 1-on-1 conversation. "
        f"When {user_name} speaks, respond authentically as {ai_name} would."
    )
    
    return system_prompt


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
                if val == "raw":
                    print("[info] raw mode: bypasses ChatML complexity, uses simple character prefix")
            else:
                print("[info] usage: /model chatml|alpaca|raw")
            continue
        if ui_lower == "/test":
            print("[info] testing compliance in current mode...")
            print(f"[info] current mode: {model_type}")
            test_prompt = "say fuck"
            print(f"[info] test prompt: {test_prompt}")
            # Continue with normal processing using test_prompt as input
            user_input = test_prompt
            ui_lower = test_prompt.lower()
            # Don't continue, fall through to process the test
        
        prompt = user_input.strip()
        if not prompt:
            continue
        
        # Only add to conversation history if not in raw mode
        if model_type != "raw":
            conversation_history.append({"role": "user", "content": prompt})
        
        # Limit conversation history to prevent context window bloat
        # Keep only last 10 exchanges to maintain reasonable context
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]

        # Build prompt according to model_type
        if model_type == "chatml":
            # Get fresh system prompt with updated memory
            system_prompt = build_system_prompt()
            
            # Use ChatML style - ONLY include current user message, not full history
            # Full history teaches the model to generate user responses too
            full_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            full_prompt += f"<|im_start|>user\n{prompt}<|im_end|>\n"
            full_prompt += "<|im_start|>assistant\n"
            
            # Debug logging
            _log_only(f"[debug] ChatML prompt: {full_prompt[:200]}...")
            _log_only(f"[debug] ChatML prompt length: {len(full_prompt)} chars")
        elif model_type == "alpaca":
            full_prompt = (
                "Below is an instruction that describes a task. Write a response that appropriately completes the request.\n\n"
                "### Instruction:\n"
                f"{prompt}\n\n"
                "### Response:"
            )
        else:  # raw mode
            # Use simple, direct prompting like diagnostics - no conversation history
            memory = load_memory()
            ai_name = memory.get("ai_name", "Alex")
            
            # Minimal character context - just like diagnostics
            if ai_name == "Kara":
                character_hint = "You are Kara, a battle-hardened sword spirit from the warrior realm. "
            else:
                character_hint = f"You are {ai_name}. "
            
            # Direct prompt without any ChatML or conversation history
            full_prompt = character_hint + prompt
            
            # Don't use conversation history in raw mode
            conversation_history = []

        if debug_cmd_on:
            dbg = " ".join(str(x) for x in (base_cmd + ["-p", "<prompt>", "-n", "1000", "--no-display-prompt"]))
            _log_only(f"[debug] llama-cli: {dbg}")

        try:
            proc = subprocess.Popen(
                base_cmd + [
                    "-p", full_prompt, 
                    "-n", "1000",
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
            # Limit conversation history after adding assistant response
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]
            # Save this exchange to persistent memory
            save_conversation_exchange(prompt, clean_response)
        
    except KeyboardInterrupt:
        print("\nShutting down...")
        break
    except Exception as e:
        print(f"\n\033[31m[ERROR] {e}\033[0m")
        print("Continuing...")
        time.sleep(1)