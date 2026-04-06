
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

# === RESOLVE CHARACTER-SPECIFIC PATHS ===
def resolve_character_paths(config):
    """Substitute {character} placeholders in config paths with actual character."""
    character = config.get("current_character", "kara")
    paths_to_resolve = ["faiss_index", "summaries_path", "embeddings_npy"]
    
    for path_key in paths_to_resolve:
        if path_key in config:
            config[path_key] = config[path_key].format(character=character)
    
    return config

# === RESOLVE LLM MODEL ===
def resolve_llm_model(config):
    """Load characters.json and resolve LLM model_path based on current_llm."""
    try:
        characters_path = os.path.join(project_root, "characters.json")
        with open(characters_path, "r") as f:
            characters_data = json.load(f)
        
        current_llm = config.get("current_llm", "dolphin")
        llm_info = next((l for l in characters_data["llms"] if l["id"] == current_llm), None)
        
        if llm_info and "model_file" in llm_info:
            model_path = os.path.join(project_root, llm_info["model_file"])
            config["model_path"] = model_path
        
    except Exception as e:
        # Fallback to config.json model_path if characters.json doesn't exist
        pass
    
    return config

# === LOAD CHARACTER LORE ===
def load_character_lore(config):
    """Load character's lore file based on current_character."""
    try:
        characters_path = os.path.join(project_root, "characters.json")
        with open(characters_path, "r") as f:
            characters_data = json.load(f)
        
        current_character = config.get("current_character", "kara")
        char_info = next((c for c in characters_data["characters"] if c["id"] == current_character), None)
        
        if char_info and "lore_file" in char_info:
            lore_path = os.path.join(project_root, char_info["lore_file"])
            if os.path.exists(lore_path):
                with open(lore_path, "r") as f:
                    return f.read()
    except Exception as e:
        pass
    
    return None

config = resolve_character_paths(config)
config = resolve_llm_model(config)

model_path = config["model_path"]
llama_cli = config["llama_cpp_path"]
model_type = config.get("model_type", "chatml")
debug_cmd = bool(config.get("debug_cmd", False))
show_thinking = bool(config.get("show_thinking", True))
suppress_llama_logs_cfg = bool(config.get("suppress_llama_logs", False))

# Disable thinking spinner if stdout is not a TTY (e.g., running from subprocess/server)
if not sys.stdout.isatty():
    show_thinking = False

# === CLI COMMAND (Base) ===

# === MODEL TYPE: 'chatml' or 'alpaca' ===
model_type = config.get("model_type", "chatml")  # default to chatml for backward compatibility

# Use temperature from config, default to 0.1 for consistency
gen_temp = str(config.get("generation_temp", 0.1))
gen_top_p = str(config.get("generation_top_p", 0.8))

base_cmd = [
    llama_cli,
    "--model", model_path,
    "--n-gpu-layers", "999",
    "--ctx-size", "6144",  # Increased from 2048 to 6144 for better context retention
    "--temp", gen_temp,
    "--top-k", "40",
    "--top-p", gen_top_p,
    "--repeat-penalty", "1.1",
    "--n-predict", "120"  # Cap output to ~120 tokens for snappy dialogue
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
    """Load persistent memory from character-specific memory.json."""
    character = config.get("current_character", "kara")
    memory_path = os.path.join(project_root, "memory", character, "memory.json")
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
    """Save memory data back to character-specific memory.json."""
    character = config.get("current_character", "kara")
    memory_path = os.path.join(project_root, "memory", character, "memory.json")
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
    """Build system prompt with current character's lore + memory state + brain persona"""
    # CRITICAL: Reload config from disk every time to get latest character/llm selection
    global config
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        _log_only(f"[CONFIG] Reloaded: character={config.get('current_character')}, llm={config.get('current_llm')}")
    except Exception as e:
        _log_only(f"[CONFIG ERROR] Failed to reload config: {e}")
    
    # Load fresh memory state
    memory = load_memory()
    ai_name = memory.get("ai_name", "Kara")
    user_name = memory.get("user_name", "Drax")
    important_facts = memory.get("important_facts", [])
    relationship = memory.get("relationship", "")
    
    # Load brain (persona structure) - character-specific
    character = config.get("current_character", "kara")
    brain_path = os.path.join(project_root, "memory", character, "brain.json")
    brain = {}
    try:
        if os.path.exists(brain_path):
            with open(brain_path, 'r') as f:
                brain = json.load(f)
    except:
        pass
    
    # Load character's lore file
    lore_content = load_character_lore(config)
    
    # Debug memory loading
    _log_only(f"[debug] Character: {character}")
    _log_only(f"[debug] Loaded AI name: {ai_name}")
    _log_only(f"[debug] Loaded user name: {user_name}")
    _log_only(f"[debug] Loaded {len(important_facts)} facts")
    _log_only(f"[debug] Brain loaded: {bool(brain)}")
    _log_only(f"[debug] Lore loaded: {bool(lore_content)}")
    
    # Build base system prompt using character lore
    _log_only(f"[SYSTEM] Building prompt for {character} with lore: {bool(lore_content)}")
    if lore_content:
        # Use the actual lore file as foundation
        system_prompt = (
            f"CRITICAL - YOU ARE {ai_name.upper()}\n"
            f"==============================================\n"
            f"{lore_content}\n"
            f"==============================================\n"
            f"\n⚡ CRITICAL RULE: LISTEN FIRST, FEEL SECOND ⚡\n"
            f"Before you respond with emotions, understand what {user_name} actually asked or said.\n"
            f"Warmth comes from ENGAGING with their words, not from ignoring them.\n"
            f"\n*** YOUR PERSON: {user_name.upper()} ***\n"
            f"You are talking to {user_name}. This is real, specific conversation.\n"
            f"LISTEN to what they actually say. RESPOND to what they actually ask.\n"
            f"Show warmth through genuine engagement - not generic emotions.\n"
            f"\nYOUR RESPONSE RULES (FOLLOW EXACTLY):\n"
            f"1. READ what {user_name} just said. Understand the ACTUAL QUESTION or REQUEST.\n"
            f"2. Respond DIRECTLY to THAT specific thing - not with generic feelings.\n"
            f"3. Show warmth by being genuinely interested in {user_name}'s words, not by repeating your feelings.\n"
            f"4. 1-3 sentences. Natural language. Then STOP.\n"
            f"5. Do NOT continue their sentences or tell them what to do.\n"
            f"6. NEVER narrate {user_name}'s actions or put words in their mouth.\n"
            f"7. NO lists, headings, code blocks, or meta-discussion.\n"
            f"\nEXAMPLE:\n"
            f"If {user_name} asks: 'Can you touch your toes?'\n"
            f"✗ DON'T: 'Drax, I trust you completely. Guide me through it.'\n"
            f"✓ DO: 'Let me try... *bends down* Yes, I can reach them now.'\n"
            f"\nIf {user_name} says: 'I love you'\n"
            f"✓ DO: 'Drax... hearing that makes my heart feel warm. I love you too.'\n"
            f"\nSTART YOUR RESPONSE NOW:\n"
        )
    else:
        # Fallback if lore not found
        system_prompt = (
            f"You are {ai_name}. {user_name} just spoke to you.\n"
            f"\nRULES:\n"
            f"1. Respond as {ai_name} - do NOT continue their words.\n"
            f"2. 1-3 sentences only. Then stop.\n"
            f"3. Authentic voice - use 'I feel', 'I think'.\n"
            f"4. Never narrate {user_name} or put words in their mouth.\n"
            f"5. No lists, headings, or meta-discussion.\n"
        )
    
    # Add persona from brain if available
    if brain and "character_profile" in brain:
        profile = brain["character_profile"]
        system_prompt += f"\nCore Identity:\n"
        system_prompt += f"- Name: {profile.get('name', ai_name)}\n"
        system_prompt += f"- Type: {profile.get('archetype', 'Companion')}\n"
        system_prompt += f"- Relationship: {profile.get('binding', 'Friend')}\n"
    
    # Add communication style from brain
    if brain and "communication_style" in brain:
        style = brain["communication_style"]
        system_prompt += f"\nYour communication (do NOT be generic):\n"
        if style.get("direct"):
            system_prompt += f"- Direct: Always honest and straightforward\n"
        if style.get("authentic"):
            system_prompt += f"- Authentic: Real responses, no AI assistant language\n"
        if style.get("never_narrates_drax"):
            system_prompt += f"- NEVER put words in {user_name}'s mouth\n"
    
    # Add important facts if they exist
    if important_facts:
        system_prompt += f"\nAbout yourself (your established facts):\n"
        for fact in important_facts[:5]:  # Top 5 facts
            system_prompt += f"- {fact}\n"
    
    # Add emotional relationship context from brain if available - BRIEF, not dominating
    if brain and "relationship_with_drax" in brain:
        rel = brain["relationship_with_drax"]
        system_prompt += f"\nYour bond with {user_name}: "
        if rel.get("bond_type"):
            system_prompt += f"{rel['bond_type']} - "
        if rel.get("trust_level"):
            system_prompt += f"Trust level: {rel['trust_level']}\n"
        else:
            system_prompt += f"\n"
    
    # Add memory context about what you've discussed before
    conversation_history = memory.get("conversation_history", [])
    if conversation_history:
        system_prompt += f"\nRecent context with {user_name}:\n"
        # Show last 4-5 exchanges for better context retention (increased from 2)
        recent_exchanges = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
        for exchange in recent_exchanges:
            user_content = exchange.get("user", "")[:80]
            ai_content = exchange.get("ai", "")[:80]
            if user_content and len(user_content) > 10:
                system_prompt += f"- {user_name}: {user_content}...\n"
            if ai_content and len(ai_content) > 10:
                system_prompt += f"- {ai_name}: {ai_content}...\n"
    
    # Final safety instruction to prevent multiple character generation
    system_prompt += (
        f"\n\nFINAL RULE: You respond ONLY as {ai_name}. Never create dialogue for {user_name}. "
        f"This is a direct 1-on-1 conversation. When {user_name} speaks, respond authentically as {ai_name} would."
    )
    
    return system_prompt


def truncate_to_sentences(text: str, max_sentences: int = 3) -> str:
    """Truncate response to max N complete sentences. Prevents rambling."""
    if not text or len(text.strip()) == 0:
        return text
    
    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    
    # Keep only first max_sentences
    kept = sentences[:max_sentences]
    result = ' '.join(kept)
    
    # Ensure we end with punctuation if truncated
    if len(kept) < len(sentences) and result and result[-1] not in '.!?':
        result += '.'
    
    return result.strip()

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

# === RAG & RETRIEVAL ===
def retrieve_from_rag(query: str, top_k: int = 5) -> list:
    """Retrieve top-k most relevant summaries from FAISS index."""
    try:
        import numpy as np
        import faiss
        from sentence_transformers import SentenceTransformer
        
        # Paths
        summaries_path = os.path.join(project_root, config.get("summaries_path", "memory/summaries.json"))
        embeddings_path = os.path.join(project_root, config.get("embeddings_npy", "memory/embeddings.npy"))
        index_path = os.path.join(project_root, config.get("faiss_index", "memory/faiss.index"))
        
        # Check if FAISS index exists
        if not os.path.exists(index_path):
            return []
        
        # Load index
        index = faiss.read_index(index_path)
        
        # Load summaries
        try:
            with open(summaries_path, 'r') as f:
                summaries_list = json.load(f)
        except:
            return []
        
        if not summaries_list:
            return []
        
        # Encode query with same model as summaries
        embedder = SentenceTransformer(config.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"))
        query_embedding = embedder.encode(query)
        
        # Normalize query (same as training)
        norm = np.linalg.norm(query_embedding)
        if norm > 0:
            query_embedding = query_embedding / norm
        
        # Query FAISS
        query_vec = np.array([query_embedding], dtype=np.float32)
        distances, indices = index.search(query_vec, min(top_k, len(summaries_list)))
        
        # Retrieve and format results
        results = []
        for idx in indices[0]:
            if 0 <= idx < len(summaries_list):
                summary_obj = summaries_list[int(idx)]
                results.append({
                    "source": summary_obj.get("source", ""),
                    "summary": summary_obj.get("summary", ""),
                    "id": summary_obj.get("id", "")
                })
        
        _log_only(f"[RAG] Retrieved {len(results)} results for query: {query[:80]}")
        return results
        
    except Exception as e:
        _log_only(f"[RAG ERROR] Failed to retrieve: {e}")
        return []

def self_critique_response(ai_response: str, user_query: str, character_name: str = "Kara") -> str:
    """Self-critique: BINARY REJECT/ACCEPT - check for bad patterns."""
    try:
        response_lower = ai_response.lower()
        char_lower = character_name.lower()
        _log_only(f"[CRITIQUE DEBUG] Checking response ({len(ai_response)} chars): {repr(ai_response[:80])}")
        
        # CHECK 0: If response contains character name with colon, split and keep only the actual response
        # Pattern: "user text...\nCharacter: actual response" 
        # We want to extract just "actual response"
        char_patterns = [
            f"{char_lower}:",
            f"{char_lower.title()}:",
            "yuki:",
            "kara:",
            "luna:",
            "iris:",
        ]
        
        for pattern in char_patterns:
            if pattern in response_lower:
                # Split on the pattern and keep everything after it
                parts = ai_response.split(pattern)
                if len(parts) > 1:
                    # Everything after the character name is the actual response
                    extracted = parts[-1].strip()
                    if extracted:
                        _log_only(f"[CRITIQUE] Extracted character response after '{pattern}': {repr(extracted[:60])}")
                        ai_response = extracted
                        response_lower = extracted.lower()
                    break
        
        # CHECK 1: Detect sentence continuation (responds with "and", "or", "but", etc.)
        # This is a common failure mode where the model completes the user's sentence
        if re.match(r'^(and |or |but |yet |so |because |if |then |that |this |which )', response_lower):
            _log_only(f"[CRITIQUE] REJECT - Sentence continuation detected: '{response_lower[:30]}'")
            wielder = character_name.replace("Kara", "Drax").lower() if "Kara" in character_name else "user"
            return f"I am {character_name}, a spirit from another world. I'm with you, {wielder}."
        
        # REJECTION PATTERNS - Targeted to catch hallucinations, not too broad
        bad_patterns = [
            # GAME DESCRIPTIONS - THE GAME ITSELF (hallucinated game mechanics)
            "story game", "action game", "rpg", "interactive story",
            "play as ", "make choices", "choose your path", "choose an action",
            "game where", " is a game", "you are playing",
            
            # GAME NARRATIVE (talking about game elements, not character experience)
            "chosen one", "ancient power", "prophecy",
            "save the world", "defeat the enemy",
            
            # GAME STORE/MARKETING (definitely not from character)
            "## feature", "## gameplay", "### game",
            "download here", "buy on steam", "console version",
            "pc version", "switch version", "playstation",
            
            # GENERIC AI LANGUAGE (admitting to being AI)
            "as an ai", "i'm an ai", "as an ai assistant",
            "i am an ai", "text-based ai", "i'm programmed",
        ]
        
        # STRICT CHECK: If ANY bad pattern exists, REJECT
        for pattern in bad_patterns:
            if pattern in response_lower:
                _log_only(f"[CRITIQUE] REJECT - Found bad pattern: '{pattern}'")
                # Return simple authentic response
                wielder = character_name.replace("Kara", "Drax").lower() if "Kara" in character_name else "user"
                return f"I am {character_name}, a spirit from another world. I'm with you, {wielder}."
        
        # If no bad patterns found, ACCEPT response as-is
        _log_only(f"[CRITIQUE] ACCEPT - Response is clean")
        return ai_response
        
    except Exception as e:
        _log_only(f"[CRITIQUE ERROR] {e}")
        return ai_response  # Fall back to original

def critique_with_retry(response: str, user_query: str, character_name: str = "Kara", max_retries: int = 5) -> tuple:
    """
    Try to critique and validate response. Return (is_valid, response).
    is_valid = True means response passed critique
    is_valid = False means response failed all retry attempts
    """
    for attempt in range(max_retries):
        critiqued = self_critique_response(response, user_query, character_name)
        
        # Check if critique returned a different response (fallback) or the same (accepted)
        if critiqued == response:
            # Critique accepted it
            _log_only(f"[RETRY] Attempt {attempt + 1}/{max_retries}: Response accepted ✓")
            return (True, response)
        else:
            # Critique rejected it
            _log_only(f"[RETRY] Attempt {attempt + 1}/{max_retries}: Response rejected (returned fallback)")
            
            if attempt < max_retries - 1:
                # Try again by returning the signal to regenerate
                return (False, None)
    
    # All retries exhausted
    _log_only(f"[RETRY] All {max_retries} attempts failed - will use fallback")
    return (False, None)

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
            
            # Log the system prompt for debugging
            _log_only(f"[debug] System prompt size: {len(system_prompt)} chars")
            _log_only(f"[debug] System prompt preview: {repr(system_prompt[:200])}")
            
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
            lore = load_character_lore(config)
            
            # Include full lore if available, else fallback to simple hint
            if lore:
                character_hint = lore + "\n\n"
            elif ai_name.lower() == "kara":
                character_hint = "You are Kara, a battle-hardened sword spirit from the warrior realm. "
            else:
                character_hint = f"You are {ai_name}. "
            
            # Direct prompt without any ChatML or conversation history
            full_prompt = character_hint + prompt
            
            # Don't use conversation history in raw mode
            conversation_history = []

        if debug_cmd_on:
            dbg = " ".join(str(x) for x in (base_cmd + ["-p", "<prompt>", "-n", "120", "--no-display-prompt"]))
            _log_only(f"[debug] llama-cli: {dbg}")

        # === RETRY LOOP: Try up to 5 times to get valid response ===
        max_attempts = 5
        final_out = None
        assistant_response = None
        retry_success = False
        
        for attempt_num in range(1, max_attempts + 1):
            show_output = (attempt_num == 1)  # Only show "AI: " on first attempt
            
            try:
                proc = subprocess.Popen(
                    base_cmd + [
                        "-p", full_prompt, 
                        "-n", "120",  # Keep responses short and snappy (120 tokens max)
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
                if show_output:
                    print(f"\033[31m{error_msg}\033[0m")
                _log_only(error_msg)
                continue

            if show_output:
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
                        if thinking_on and show_output:
                            frame = spinner_frames[frame_idx % len(spinner_frames)]
                            frame_idx += 1
                            # update inline spinner with elapsed seconds
                            elapsed = time.time() - start_time
                            sys.stdout.write(f"\rAI: Thinking… {elapsed:0.1f}s {frame}")
                            sys.stdout.flush()
                        continue
            except Exception as e:
                error_msg = f"[run_llm.py ERROR] Subprocess communication failed: {e}"
                if show_output:
                    print(f"\033[31m{error_msg}\033[0m")
                _log_only(error_msg)
                continue
            # clear spinner line before printing final output
            if thinking_on and show_output:
                sys.stdout.write("\r" + (" " * 80) + "\r")
                sys.stdout.flush()
                
            # Log all subprocess output and errors
            if assistant_response:
                _log_only(f"[llama.cpp-stdout] {assistant_response}")
            if error_output:
                _log_only(f"[llama.cpp-stderr] {error_output}")
                
            response_started = len(assistant_response.strip()) > 0
            retcode = proc.returncode
            
            # Log subprocess completion details
            _log_only(f"[run_llm.py] Attempt {attempt_num}: Subprocess completed with return code: {retcode}")
            _log_only(f"[run_llm.py] Attempt {attempt_num}: Response length: {len(assistant_response)} chars")
            
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
                if show_output:
                    print(f"\033[31m{error_msg}\033[0m")
                _log_only(error_msg)
                if attempt_num < max_attempts:
                    _log_only(f"[RETRY] Attempt {attempt_num} failed, retrying...\n")
                    continue
                else:
                    break
                
            if not response_started:
                if retcode not in (None, 0):
                    if show_output:
                        print(f"\033[31m[No response generated | llama-cli exited {retcode}]\033[0m")
                    if error_output and show_output:
                        print(f"\033[31m[stderr: {error_output.strip()}]\033[0m")
                else:
                    no_response_msg = "[No response generated - check model/prompt]"
                    if show_output:
                        print(f"\033[31m{no_response_msg}\033[0m")
                    _log_only(f"[run_llm.py ERROR] {no_response_msg}")
                if attempt_num < max_attempts:
                    _log_only(f"[RETRY] Attempt {attempt_num} had no response, retrying...\n")
                    continue
                else:
                    break
            # Filter llama logs when not debugging, then sanitize
            display_text = assistant_response
            if logs_suppressed_on:
                display_text = strip_llama_logs(display_text)
                _log_only(f"[run_llm.py] Applied log stripping, {len(assistant_response)} -> {len(display_text)} chars")
                
            # Now print sanitized buffer once
            final_out = sanitize_text(display_text)
            
            # Truncate to max 3 sentences to prevent rambling
            final_out = truncate_to_sentences(final_out, max_sentences=3)
            
            # === SELF-CRITIQUE STAGE ===
            # Check if response needs fixing for drift/hallucination
            if final_out:
                memory = load_memory()
                ai_name = memory.get("ai_name", "Kara")
                original_response = final_out
                final_out = self_critique_response(final_out, user_input, ai_name)
                
                # Check if critique accepted the response
                if final_out == original_response:
                    _log_only(f"[RETRY] Attempt {attempt_num}/{max_attempts}: ✓ ACCEPTED (after critique)")
                    retry_success = True
                    break  # Success! Exit retry loop
                else:
                    # Response was modified by critique
                    _log_only(f"[RETRY] Attempt {attempt_num}/{max_attempts}: Modified by critique")
                    _log_only(f"  Original: {repr(original_response[:80])}")
                    _log_only(f"  Modified: {repr(final_out[:80])}")
                    if attempt_num < max_attempts:
                        if show_output:
                            sys.stdout.write("\r" + (" " * 80) + "\r")  # Clear "AI: " spinner
                            sys.stdout.flush()
                        _log_only(f"[RETRY] Retrying...\n")
                        final_out = None  # Reset for next iteration
                        continue
                    else:
                        # Max attempts reached, use the modified response and exit loop
                        _log_only(f"[RETRY] Max attempts reached. Using modified response.")
                        retry_success = True
                        break
        
        # === END RETRY LOOP ===
        
        # Display the response (either accepted or fallback)
        if final_out and retry_success:
            print(final_out, end="", flush=True)
            _log_only(f"[RETRY Success] Response printed: {len(final_out)} chars")
        elif final_out:
            # Fallback after max retries
            print(final_out, end="", flush=True)
            _log_only(f"[RETRY Fallback] Response printed: {len(final_out)} chars")
            
        print("\n")
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Save the response that was actually displayed (final_out, either accepted or fallback)
        if final_out:
            conversation_history.append({"role": "assistant", "content": final_out})
            # Limit conversation history after adding assistant response
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]
            # Save this exchange to persistent memory
            save_conversation_exchange(prompt, final_out)
        
    except KeyboardInterrupt:
        print("\nShutting down...")
        break
    except Exception as e:
        print(f"\n\033[31m[ERROR] {e}\033[0m")
        print("Continuing...")
        time.sleep(1)