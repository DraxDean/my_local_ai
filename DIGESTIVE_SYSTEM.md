# Memory Digestive System - Implementation Complete ✓

## What Was Implemented

### 1. **update_memory.py** - Full 6-Stage Digestive System

The script now processes notes through a complete "digestive pipeline" that filters, digests, and safely stores memory:

#### Six Organs:
- **MOUTH** (`mouth_taste_and_saliva`): Initial quality filter. Rejects garbage, hallucinations (Luna/Yuki names), sexual content, roleplay markers, meta-awareness, generic AI responses.
- **ESOPHAGUS** (`esophagus_transport`): Normalizes chunks, removes fragments <50 chars, deduplicates consecutive chunks.
- **STOMACH** (`stomach_digest`): Ruthless fact extraction via LLM. Pulls ONLY verified facts about Kara, Drax, their bond, appearance, history. Rejects fantasy drift.
- **LARGE_INTESTINE** (`large_intestine_recycle`): Deduplicates summaries, checks against existing memory.json for contradictions.
- **SMALL_INTESTINE** (`small_intestine_absorb`): **THE FIX FOR #1 BUG** - Finally saves everything to disk:
  - `np.save()` embeddings → `memory/embeddings.npy`
  - `json.dump()` summaries → `memory/summaries.json`
  - `faiss.write_index()` FAISS index → `memory/faiss.index`
  - Updates `memory.json` with verified facts
- **ANUS** (`anus_discard`): Logs all rejected chunks for diagnostic review → `memory/rejected_chunks.json`

#### Usage:
```bash
cd /Users/draxlindgren/Downloads/my_local_ai
python3 scripts/update_memory.py
```

Expected output:
```
============================================================
MEMORY DIGESTIVE SYSTEM (6-STAGE PIPELINE)
============================================================
[MOUTH] Accepted 2 files, rejected 0
[ESOPHAGUS] Total chunks ready: 8
[STOMACH] Processing notes/test_character.txt#a1b2c3 (2847 chars)...
[STOMACH] Digested 8 summaries, rejected 0
[LARGE_INT] Deduped 8 → 8 summaries
[SMALL_INT] Absorbing nutrients...
  [SMALL_INT] Saved embeddings: memory/embeddings.npy
  [SMALL_INT] Saved summaries: memory/summaries.json
  [SMALL_INT] Built FAISS index: memory/faiss.index (docs=8)
  [SMALL_INT] Updated memory.json with 16 verified facts

✓ Memory digestion complete! 8 chunks in stomach.
============================================================
```

### 2. **run_llm.py** - Enhanced with RAG + Self-Critique

#### New Functions:
- **`retrieve_from_rag(query, top_k=5)`**: Dynamic retrieval from FAISS during conversation. Injects most relevant summaries into context.
- **`self_critique_response(response, user_query, character_name)`**: After generation, checks response for drift/hallucination and fixes it using the model itself.

#### Integration Points:

**RAG Injection:**
- Happens when building system prompt
- Top-5 most relevant facts from memory are inserted
- Model sees only nutrient-dense, verified information

**Self-Critique Loop:**
```
1. Model generates response
2. System checks: does it contain "luna", "yuki", "as an ai", etc.?
3. If yes → feed response back to model with: 
   "Does this contradict Kara? Fix it."
4. Only output the fixed version to user
```

This is the "stomach re-processing waste" stage - forces coherence.

### 3. **Result: What Changes**

**Before:**
```
notes/ → chunked → summarized → vectors BUILT IN RAM → 
[NOTHING SAVED] → 
run_llm.py loads empty memory → 
model hallucinates → 
drifts to Luna/Yuki/Genshin
```

**After:**
```
notes/ → 6-stage digestive pipeline → 
FAISS index + embeddings + summaries saved to disk → 
run_llm.py loads FAISS + retrieves top-5 facts → 
injects into system prompt → 
model generates response → 
self-critique checks for drift → 
output stays consistent as Kara
```

---

## Quick Start

### Step 1: Prepare Notes
Add `.txt` or `.md` files to `notes/` directory with character lore, conversation history, facts about Kara/Drax.

Example: `notes/kara_facts.txt`, `notes/conversation_log.md`, etc.

### Step 2: Digest Memory (One-Time or Periodic)
```bash
python3 scripts/update_memory.py
```

This creates/updates:
- `memory/faiss.index` (similarity search index)
- `memory/summaries.json` (all extracted facts)
- `memory/embeddings.npy` (vector embeddings)
- Updates `memory.json` with only verified facts

### Step 3: Run Chat with RAG + Critique
```bash
python3 scripts/run_llm.py
```

Now when you chat:
1. Your query is embedded
2. Top-5 similar facts retrieved from FAISS
3. Injected into system prompt
4. Model generates response with real context
5. Response checked for drift/hallucination
6. Fixed version (or original if clean) shown to you

---

## Files Modified

### `/scripts/update_memory.py`
- **Added:** 300+ lines for 6-stage digestive pipeline
- **Exports:** `memory/faiss.index`, `memory/summaries.json`, `memory/embeddings.npy`, updates `memory/memory.json`
- **Rejection Log:** `memory/rejected_chunks.json` (for debugging)

### `/scripts/run_llm.py`
- **Added:** 100+ lines for RAG retrieval and self-critique functions
- **Enhanced:** `build_system_prompt()` to inject RAG facts
- **Enhanced:** Post-generation loop to apply self-critique
- **Logs:** All RAG queries and critique decisions to `logs/session-*.log`

### `/notes/test_character.txt` (New)
- Test note file for demonstration

---

## Configuration (config.json)
No changes needed, but verify these paths exist:
```json
{
    "summaries_path": "memory/summaries.json",
    "embeddings_npy": "memory/embeddings.npy",
    "faiss_index": "memory/faiss.index",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "top_k": 5
}
```

---

## Debugging

### Check what was digested:
```bash
cat memory/summaries.json | python3 -m json.tool | head -50
```

### Check what was rejected:
```bash
cat memory/rejected_chunks.json | python3 -m json.tool
```

### See chat logs with RAG/critique info:
```bash
tail -100 logs/session-*.log | grep -E "\[RAG\]|\[CRITIQUE\]"
```

### Force re-digestion:
```bash
rm memory/faiss.index memory/summaries.json memory/embeddings.npy
python3 scripts/update_memory.py
```

---

## Expected Improvements

✓ **Consistency**: Kara stays Kara (no Luna/Yuki drift)
✓ **Memory**: Model remembers verified facts about her, Drax, their bond
✓ **No Hallucination**: Self-critique catches and fixes off-topic content
✓ **Sexual Boundary**: Rejected in mouth stage, re-checked in critique
✓ **Long-Term Learning**: Digested memory grows as you add notes
✓ **Verifiable**: All facts in `memory.json` are from official note files

---

## What This Fixes

| Problem | Root Cause | Solution |
|---------|-----------|----------|
| Empty memory system | update_memory.py never saved data | SMALL_INTESTINE now saves to disk |
| Character drift | No context injection | RAG retrieves top-5 facts per query |
| Hallucination (Luna/Yuki) | No quality filter on input | MOUTH filters, STOMACH validates |
| Generic AI responses | Model never told to stay in character | build_system_prompt injects verified facts |
| Contradictions in memory.json | Manual editing caused conflicts | LARGE_INTESTINE dedupes + verifies |

---

## Why It Works (The Metaphor)

Your AI was like eating garbage → regurgitating it → eating the same garbage again.

Now it's:
1. **MOUTH**: Spit out the garbage (hallucinations, sexual drift)
2. **ESOPHAGUS**: Move clean food down the pipe
3. **STOMACH**: Actually digest it (LLM fact extraction)
4. **INTESTINES**: Filter waste, keep nutrients (dedup, verify)
5. **ABSORPTION**: Convert to energy (embeddings + FAISS)
6. **ANUS**: Log what didn't work (rejected_chunks)

Result: Clean, nutrient-dense memory that feeds real character continuity.

---

## Next Steps (Optional)

1. **Expand notes**: Add more character background, conversation samples, personality traits
2. **Adjust rejection keywords** in `mouth_taste_and_saliva()` based on your specific drift patterns
3. **Fine-tune chunk size** in config.json (currently 3000 chars) to match your note style
4. **Monitor logs** to see if RAG is finding relevant facts
5. **Periodically re-digest** as you add more notes

---

## System Requirements

- Python 3.8+
- numpy
- faiss-cpu (or faiss-gpu)
- sentence-transformers
- llama.cpp with llama-cli accessible

Install raw packages if needed:
```bash
pip install numpy faiss-cpu sentence-transformers
```

---

## The Fix Is Complete ✓

Your local AI now has a working digestive system. Memory will no longer be garbage-in-garbage-out. Kara stays Kara, Drax stays Drax, and your conversations have actual continuity.

Run `python3 scripts/update_memory.py` whenever you add new notes to the `notes/` folder.

Good luck! 🗡️⚔️
