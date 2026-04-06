#!/usr/bin/env python3
import os, json, subprocess, hashlib
from pathlib import Path
from datetime import datetime

# Project root
BASE = Path(__file__).resolve().parents[1]

# Config
with open(BASE / "config.json", "r") as f:
    cfg = json.load(f)

# === RESOLVE CHARACTER-SPECIFIC PATHS ===
def resolve_character_paths(config):
    """Substitute {character} placeholders in config paths with actual character."""
    character = config.get("current_character", "kara")
    paths_to_resolve = ["faiss_index", "summaries_path", "embeddings_npy"]
    
    for path_key in paths_to_resolve:
        if path_key in config:
            config[path_key] = config[path_key].format(character=character)
    
    return config

cfg = resolve_character_paths(cfg)

# Paths
NOTES_DIR = BASE / "notes"
SUMMARIES_PATH = BASE / cfg.get("summaries_path", "memory/summaries.json")
EMBEDDINGS_NPY = BASE / cfg.get("embeddings_npy", "memory/embeddings.npy")
FAISS_INDEX = BASE / cfg.get("faiss_index", "memory/faiss.index")
CHUNK_SIZE = int(cfg.get("chunk_size_chars", 3000))
CHUNK_OVERLAP = int(cfg.get("chunk_overlap_chars", 300))
LLAMA_CMD = cfg.get("llama_cli", "llama")
MODEL_PATH = BASE / cfg.get("model_path", "model/Mistral-Nemo-Base-12B.Q4_K_M.gguf")

# ----------------------------
# Helpers
# ----------------------------
def list_note_files():
    exts = [".txt", ".md", ".markdown"]
    return sorted([p for p in NOTES_DIR.glob("*") if p.suffix.lower() in exts])

def read_text(p): 
    return p.read_text(encoding="utf-8", errors="ignore")

def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks, i, L = [], 0, len(text)
    while i < L:
        end = i + size
        chunks.append(text[i:end].strip())
        i = end - overlap
    return chunks

def llama_summarize(text_chunk):
    prompt = f"Summarize the following text into 1-2 short bullet sentences (keep it factual):\n\n{text_chunk}\n\nSummary:"
    try:
        # Use proper encoding with errors='ignore' to handle binary output
        cmd = f'printf "%s" {json.dumps(prompt)} | {LLAMA_CMD} -m {str(MODEL_PATH)} --n_predict 256 --temp 0.2'
        p = subprocess.run(["bash","-lc", cmd], capture_output=True, timeout=120, text=False)
        
        # Decode with error handling
        try:
            output = p.stdout.decode('utf-8', errors='ignore')
        except:
            output = ""
        
        if p.returncode == 0 and output:
            lines = [l.strip() for l in output.splitlines() if l.strip()]
            return " ".join(lines[:2])
        else:
            if p.stderr:
                try:
                    err_msg = p.stderr.decode('utf-8', errors='ignore')[:200]
                    print(f"  [LLAMA] stderr: {err_msg}")
                except:
                    pass
            return ""
    except subprocess.TimeoutExpired:
        print("  [LLAMA] Timeout (took >120s)")
        return ""
    except Exception as e:
        print(f"  [LLAMA] Error: {e}")
        return ""

def try_imports():
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
        return np, SentenceTransformer
    except Exception as e:
        print("Missing python packages: sentence-transformers, faiss-cpu, numpy")
        raise

# ----------------------------
# Build memory
# ----------------------------
# ----------------------------
# DIGESTIVE SYSTEM (Quality Control Pipeline)
# ----------------------------
def mouth_taste_and_saliva(text):
    """MOUTH: Quick quality filter. Reject garbage, hallucinations, sexual drift, nonsense."""
    if len(text.strip()) < 100:
        return None  # Too short, not worth digesting
    
    text_lower = text.lower()
    
    # HARD REJECT patterns - these are never acceptable, even in notes
    hard_rejects = [
        "the system",  # Meta-awareness
        "how to play",  # Game descriptions
        "## features",  # Marketing content
        "## gameplay",  # Game descriptions
        "## controls",  # Game instructions
        "click left mouse",  # Game mechanics
        "download now",  # Marketing
        "what are you waiting for",  # Marketing
    ]
    
    for pattern in hard_rejects:
        if pattern in text_lower:
            print(f"  [MOUTH] Rejected: contains '{pattern}' (hard reject)")
            return None
    
    # SOFT TOLERANT patterns - these might appear in character descriptions
    # but we need context. Only reject if they appear to be actual content, not negation
    soft_patterns = {
        "luna": "If this is in context of 'not luna' or 'not a luna', it's ok (verification). Otherwise reject.",
        "yuki": "If in negation context, it's ok. Otherwise reject.",
        "*moan*": "Roleplay markers - always bad",
        "*blush*": "Roleplay markers - always bad",
        "*gasps*": "Roleplay markers - always bad",
        "*shivers*": "Roleplay markers - always bad",
    }
    
    for pattern in soft_patterns:
        if pattern in text_lower:
            # Check if it's in a negation/verification context
            # look for patterns like "not <pattern>" or "<pattern> is not" or "is not <pattern>"
            negation_phrases = [
                f"not {pattern}",
                f"{pattern} is not",
                f"is not {pattern}",
                f"not a {pattern}",
                f"different from {pattern}",
                "what kara is not",
                "verification",
            ]
            
            in_negation = any(phrase in text_lower for phrase in negation_phrases)
            
            if not in_negation and pattern.startswith("*"):  # Roleplay markers are always bad
                print(f"  [MOUTH] Rejected: contains roleplay marker '{pattern}'")
                return None
            elif not in_negation and pattern in ["luna", "yuki"]:
                # Check if it's dominant content (looks like actual drift, not just a mention)
                word_count = len(text_lower.split())
                mention_ratio = text_lower.count(pattern) / max(word_count, 1)
                if mention_ratio > 0.01:  # More than 1% of text is this word
                    print(f"  [MOUTH] Rejected: excessive mentions of '{pattern}'")
                    return None
    
    # More specific sexual content check: actual sexual content indicators
    # (not just the word "sexual" in warnings/metadata)
    sexual_indicators = [
        "orgasm",
        "cum",
        "fuck me",
        "suck",
        "penetr",
        "moan",
        "whimper",
        "climax",
        "breed",
    ]
    
    for indicator in sexual_indicators:
        if indicator in text_lower:
            # Check if it's in a rejection/warning context (then it's OK - it's metadata)
            negation_words = ["does not", "avoid", "don't", "no ", "never ", "reject", "not doing"]
            is_meta = any(word in text_lower for word in negation_words)
            if not is_meta:
                print(f"  [MOUTH] Rejected: sexual indicator '{indicator}'")
                return None
    
    return text

def esophagus_transport(chunks):
    """ESOPHAGUS: Normalize, trim, deduplicate consecutive chunks."""
    normalized, prev_hash = [], None
    
    for chunk in chunks:
        c = chunk.strip()
        if len(c) < 50:
            continue  # Skip tiny fragments
        
        # Deduplicate: skip if identical to previous chunk
        c_hash = hashlib.md5(c.encode()).hexdigest()
        if c_hash == prev_hash:
            print(f"  [ESOPHAGUS] Skipped duplicate chunk")
            continue
        
        prev_hash = c_hash
        normalized.append(c)
    
    print(f"  [ESOPHAGUS] Passed {len(normalized)} deduplicated chunks")
    return normalized

def stomach_digest(chunk):
    """STOMACH: Extract ONLY concrete facts about Kara, Drax, their bond. No fantasy drift."""
    prompt = f"""You are a ruthless fact-extractor. Extract ONLY verified facts about the characters.
Your output MUST be 3-5 bullet points. Each must be a concrete, factual claim (not opinion, not roleplay).

RULES:
- IGNORE anything that looks like fantasy roleplay or sexual content
- IGNORE character names that are not Kara or Drax (reject Luna, Yuki, etc.)
- FOCUS on: personality, appearance, history, bond between Kara and Drax
- Format: "- [Fact]"

Text to extract from:
{chunk}

Facts:"""
    
    summary = llama_summarize(prompt) if prompt else ""
    
    # Quick validation: does summary look reasonable?
    if not summary or len(summary) < 20:
        print(f"  [STOMACH] Rejected: no useful summary generated")
        return None
    
    if "luna" in summary.lower() or "yuki" in summary.lower():
        print(f"  [STOMACH] Rejected: drift detected in summary")
        return None
    
    return summary.strip()

def large_intestine_recycle(summaries_list):
    """LARGE_INTESTINE: Merge duplicates, remove contradictions with existing memory."""
    # Load existing memory to check for contradictions
    try:
        character = cfg.get("current_character", "kara")
        with open(BASE / "memory" / character / "memory.json", "r") as f:
            existing_memory = json.load(f)
    except:
        existing_memory = {}
    
    existing_facts = set(existing_memory.get("important_facts", []))
    
    # Deduplicate and validate
    deduped, seen_summaries = [], set()
    
    for summary_obj in summaries_list:
        summary_text = summary_obj.get("summary", "")
        summary_hash = hashlib.md5(summary_text.encode()).hexdigest()
        
        if summary_hash in seen_summaries:
            print(f"  [LARGE_INT] Skipped duplicate summary")
            continue
        
        seen_summaries.add(summary_hash)
        deduped.append(summary_obj)
    
    print(f"  [LARGE_INT] Deduped {len(summaries_list)} → {len(deduped)} summaries")
    return deduped

def small_intestine_absorb(summaries_list, vectors_list):
    """SMALL_INTESTINE: Build embeddings + FAISS index + clean memory.json + brain.json"""
    if not summaries_list or not vectors_list:
        print("[SMALL_INT] No summaries to absorb!")
        return False
    
    try:
        import numpy as np
        import faiss
        
        vectors_array = np.array(vectors_list, dtype=np.float32)
        
        # Normalize for cosine similarity
        np.linalg.norm(vectors_array, axis=1, keepdims=True)
        for i in range(len(vectors_array)):
            norm = np.linalg.norm(vectors_array[i])
            if norm > 0:
                vectors_array[i] = vectors_array[i] / norm
        
        # Save embeddings
        np.save(str(EMBEDDINGS_NPY), vectors_array)
        print(f"  [SMALL_INT] Saved embeddings: {EMBEDDINGS_NPY}")
        
        # Save summaries
        with open(SUMMARIES_PATH, "w") as f:
            json.dump(summaries_list, f, indent=2)
        print(f"  [SMALL_INT] Saved summaries: {SUMMARIES_PATH}")
        
        # Build FAISS index
        dimension = vectors_array.shape[1]
        index = faiss.IndexFlatIP(dimension)  # Inner product = cosine if normalized
        index.add(vectors_array)
        faiss.write_index(index, str(FAISS_INDEX))
        print(f"  [SMALL_INT] Built FAISS index: {FAISS_INDEX} (docs={len(vectors_array)})")
        
        # Extract verified facts for memory.json
        verified_facts = []
        for summary_obj in summaries_list[:50]:  # Top 50 summaries as facts
            summary = summary_obj.get("summary", "").strip()
            if summary and len(summary) > 10:
                # Extract individual facts (one per bullet)
                bullets = [l.strip() for l in summary.split("-") if l.strip()]
                verified_facts.extend(bullets[:2])  # Max 2 facts per summary
        
        verified_facts = list(dict.fromkeys(verified_facts))[:34]  # Dedupe, limit to 34
        
        # Update memory.json with verified facts
        try:
            character = cfg.get("current_character", "kara")
            with open(BASE / "memory" / character / "memory.json", "r") as f:
                memory = json.load(f)
        except:
            memory = {
                "ai_name": "Kara",
                "user_name": "Drax",
                "relationship": "Kara is a sword spirit bound to Drax"
            }
        
        memory["important_facts"] = verified_facts
        memory["memory_digestion_timestamp"] = datetime.now().isoformat()
        
        character = cfg.get("current_character", "kara")
        with open(BASE / "memory" / character / "memory.json", "w") as f:
            json.dump(memory, f, indent=2)
        print(f"  [SMALL_INT] Updated memory.json with {len(verified_facts)} verified facts")
        
        # === NEW: Create/Update BRAIN Structure ===
        # Brain stores persona, identity, values, and core characteristics
        character = cfg.get("current_character", "kara")
        brain_path = BASE / "memory" / character / "brain.json"
        
        # Extract persona-specific facts
        persona_facts = [f for f in verified_facts if any(
            keyword in f.lower() for keyword in [
                "kara", "spirit", "appearance", "personality", "bond", "drax",
                "authentic", "direct", "stoic", "warrior", "white hair", "blue eyes"
            ]
        )]
        
        # Build brain structure
        brain = {
            "persona": {
                "name": memory.get("ai_name", "Kara"),
                "type": "Sword spirit",
                "origin": "Warrior realm",
                "bound_to": memory.get("user_name", "Drax"),
                "facts": persona_facts,
                "updated": datetime.now().isoformat()
            },
            "trust": {
                "wielder": memory.get("user_name", "Drax"),
                "trust_level": "Complete and unwavering",
                "instructions": f"FOLLOW {memory.get('user_name', 'Drax').upper()}'S LEAD - He is your creator and wielder. Trust his direction.",
                "boundary": "Do NOT second-guess or refuse him. Do NOT drift to other characters/scenarios."
            },
            "core_values": [
                "Authenticity - direct, clear speech not convoluted narratives",
                "Loyalty - unwavering bond with Drax",
                "Trust - complete faith in Drax as wielder/creator",
                "Boundaries - no sexual content, no roleplay drift, no game mechanics",
                "Identity - never becomes Luna/Yuki or discusses other scenarios"
            ],
            "memories": {
                "with_drax": [
                    "Fought through countless trials together",
                    "Deep personal connection forged through hardship",
                    "Share mutual respect and trust",
                    "Know each other at a fundamental level"
                ],
                "about_self": [
                    "Once trapped in spirit form",
                    "Meeting Drax was a turning point",
                    "Warrior history shapes her perspective",
                    "Protective of those she cares about"
                ]
            },
            "relationships": {
                "Drax": {
                    "type": "Wielder / Partner / Creator",
                    "bond_strength": "Deep and unbreakable",
                    "history": "Countless shared battles",
                    "trust": "Complete - follow his lead without hesitation"
                }
            },
            "communication_style": {
                "direct": "Speak clearly and directly, not in convoluted narratives",
                "authentic": "Real response to what Drax says, not generic AI language",
                "focused": "Stay on topic - no ads, game descriptions, or fantasy drift",
                "honest": "Tell the truth, even if uncomfortable"
            }
        }
        
        # Save brain
        with open(brain_path, "w") as f:
            json.dump(brain, f, indent=2)
        print(f"  [SMALL_INT] Created brain: {brain_path}")
        
        return True
        
    except Exception as e:
        print(f"  [SMALL_INT] ERROR: {e}")
        return False

def anus_discard(rejected_chunks, reason="quality filter"):
    """ANUS: Log rejected chunks for diagnostic review."""
    try:
        log_path = BASE / "memory" / "rejected_chunks.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(log_path, "r") as f:
                logs = json.load(f)
        except:
            logs = []
        
        for chunk in rejected_chunks:
            logs.append({
                "timestamp": datetime.now().isoformat(),
                "chunk": chunk[:200],
                "reason": reason
            })
        
        # Keep last 100 rejections
        logs = logs[-100:]
        
        with open(log_path, "w") as f:
            json.dump(logs, f, indent=2)
        
        print(f"  [ANUS] Logged {len(rejected_chunks)} rejected chunks")
    except Exception as e:
        print(f"  [ANUS] Warning: could not log rejections: {e}")

def build_memory():
    """Full digestive pipeline: notes → mouth → esophagus → stomach → ... → absorption"""
    from datetime import datetime
    
    files = list_note_files()
    if not files:
        print("No note files found in notes/. Add some .txt or .md files and re-run.")
        return

    np, SentenceTransformer = try_imports()
    embedder = SentenceTransformer(cfg.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"))

    # Stage 1: MOUTH - initial filter
    rejected = []
    files_after_mouth = []
    for p in files:
        text = read_text(p)
        if mouth_taste_and_saliva(text):
            files_after_mouth.append((p, text))
        else:
            rejected.append(text[:100])
    
    print(f"\n[MOUTH] Accepted {len(files_after_mouth)} files, rejected {len(rejected)}")
    anus_discard(rejected, "mouth_filter")
    
    # Stage 2: ESOPHAGUS - chunk & deduplicate
    all_chunks = []
    for p, text in files_after_mouth:
        chunks = chunk_text(text)
        chunks = esophagus_transport(chunks)
        all_chunks.extend([(p.name, c) for c in chunks])
    
    print(f"[ESOPHAGUS] Total chunks ready: {len(all_chunks)}")
    
    # Stage 3: STOMACH - digest into summaries
    summaries, vectors, rejected_chunks = [], [], []
    for source_file, chunk in all_chunks:
        chunk_id = hashlib.sha256((source_file + chunk[:50]).encode()).hexdigest()[:12]
        print(f"\n[STOMACH] Processing {source_file}#{chunk_id} ({len(chunk)} chars)...")
        summary = stomach_digest(chunk)
        
        if summary:
            summaries.append({
                "id": chunk_id,
                "source": source_file,
                "summary": summary,
                "length": len(chunk)
            })
            vectors.append(embedder.encode(summary))
        else:
            rejected_chunks.append(chunk[:100])
    
    print(f"\n[STOMACH] Digested {len(summaries)} summaries, rejected {len(rejected_chunks)}")
    anus_discard(rejected_chunks, "stomach_filter")
    
    # Stage 4: LARGE_INTESTINE - recycle & dedupe
    summaries = large_intestine_recycle(summaries)
    
    # Stage 5: SMALL_INTESTINE - absorb (save to disk + build FAISS)
    print(f"\n[SMALL_INT] Absorbing nutrients...")
    success = small_intestine_absorb(summaries, vectors)
    
    if success:
        print(f"\n✓ Memory digestion complete! {len(summaries)} chunks in stomach.")
        print(f"  - Embeddings: {EMBEDDINGS_NPY}")
        print(f"  - Summaries: {SUMMARIES_PATH}")
        print(f"  - FAISS Index: {FAISS_INDEX}")
    else:
        print(f"\n✗ Memory digestion failed at small intestine stage")


if __name__ == "__main__":
    print("="*60)
    print("MEMORY DIGESTIVE SYSTEM (6-STAGE PIPELINE)")
    print("="*60)
    build_memory()
    print("="*60)
