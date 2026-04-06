# Multi-Character & Multi-LLM System

## Overview

This system supports multiple character cards and multiple LLM models with **independent memory storage for each character**. Each character maintains their own conversation history, persona data, and learned facts.

## Architecture

```
characters.json          ← Central registry of all characters and LLMs
├──> character configs
│    ├─ id, name, description
│    └─ lore_file, memory_folder, active status
└──> llm configs
     ├─ id, name, model_file
     └─ active status

config.json              ← Current selections (updated by start.py)
├─ current_character: "kara"
└─ current_llm: "dolphin"

memory/
├─ kara/
│  ├─ memory.json       (Kara's conversation history)
│  ├─ brain.json        (Kara's persona data)
│  ├─ faiss.index       (Kara's semantic index)
│  ├─ summaries.json    (Kara's fact summaries)
│  └─ embeddings.npy    (Kara's embeddings)
├─ luna/
│  ├─ memory.json
│  ├─ brain.json
│  └─ ...
└─ iris/
   ├─ memory.json
   ├─ brain.json
   └─ ...
```

## Key Features

### 1. Character Separation
Each character has **completely isolated memory**:
- `memory/{character_name}/memory.json` - Conversation history
- `memory/{character_name}/brain.json` - Persona and characteristics
- `memory/{character_name}/faiss.index` - Semantic search index
- `memory/{character_name}/summaries.json` - Extracted facts

**Example:** Kara can talk to Drax, Luna can have completely different conversations with a different user, with no memory overlap.

### 2. LLM Flexibility
Switch between different models without affecting character memory:
- Kara + Dolphin → Uses Kara's memory
- Kara + MythoMax → Uses **same** Kara memory, different LLM
- Luna + Dolphin → Uses Luna's separate memory

**Result:** Same character with different models or same character with same model = shared memory.

### 3. Interactive Selection
When you run `python3 start.py`:
1. Choose which character to talk to (Kara, Luna, Iris, etc.)
2. Choose which LLM to use (Dolphin, MythoMax, OpenHermes)
3. System resolves paths and launches chat

## Configuration Files

### characters.json
Defines all available characters and LLMs:

```json
{
  "characters": [
    {
      "id": "kara",
      "name": "Kara",
      "description": "A spirit companion from another world",
      "lore_file": "notes/kara_verified_lore.txt",
      "memory_folder": "memory/kara",
      "active": true
    },
    {
      "id": "luna",
      "name": "Luna",
      "description": "A mystical guide (coming soon)",
      "lore_file": "notes/luna_lore.txt",
      "memory_folder": "memory/luna",
      "active": false
    }
  ],
  "llms": [
    {
      "id": "dolphin",
      "name": "Dolphin 2.9.3",
      "model_file": "model/dolphin-2.9.3-mistral-nemo-12b.Q4_K_M.gguf",
      "active": true,
      "description": "Focused, conversational model"
    },
    {
      "id": "mythomax",
      "name": "MythoMax 13B",
      "model_file": "model/mythomax-l2-13b.Q4_K_M.gguf",
      "active": true,
      "description": "Creative, storytelling model"
    }
  ]
}
```

### config.json (Paths with Placeholders)
Uses `{character}` placeholder that's resolved at runtime:

```json
{
    "current_character": "kara",
    "current_llm": "dolphin",
    "faiss_index": "memory/{character}/faiss.index",
    "summaries_path": "memory/{character}/summaries.json",
    "embeddings_npy": "memory/{character}/embeddings.npy",
    ...
}
```

At runtime, `{character}` is replaced with the selected character, e.g.:
- `memory/{character}/faiss.index` → `memory/kara/faiss.index`

## How It Works

### 1. Character Selection (start.py)
```python
characters_data = load_characters()
selected_character = select_character(characters_data, current_character)
selected_llm = select_llm(characters_data, current_llm)
update_config("config.json", selected_character, selected_llm)
```

### 2. Path Resolution (run_llm.py & update_memory.py)
```python
def resolve_character_paths(config):
    """Substitute {character} placeholders with actual character."""
    character = config.get("current_character", "kara")
    paths_to_resolve = ["faiss_index", "summaries_path", "embeddings_npy"]
    
    for path_key in paths_to_resolve:
        if path_key in config:
            config[path_key] = config[path_key].format(character=character)
    
    return config
```

### 3. LLM Resolution (run_llm.py)
```python
def resolve_llm_model(config):
    """Load characters.json and set model_path based on current_llm."""
    characters_data = json.load(open("characters.json"))
    current_llm = config.get("current_llm", "dolphin")
    llm_info = next((l for l in characters_data["llms"] if l["id"] == current_llm))
    config["model_path"] = llm_info["model_file"]
    return config
```

## Usage

### Basic Usage
```bash
# Start the system
python3 start.py

# Then choose:
# 1. Select character (Kara, Luna, etc.)
# 2. Select LLM (Dolphin, MythoMax, etc.)
# 3. Chat automatically starts
```

### Adding a New Character
1. Add entry to `characters.json`:
   ```json
   {
     "id": "sylvia",
     "name": "Sylvia",
     "description": "Clever artificer from the north",
     "lore_file": "notes/sylvia_lore.txt",
     "memory_folder": "memory/sylvia",
     "active": false
   }
   ```

2. Create memory folder:
   ```bash
   mkdir -p memory/sylvia
   ```

3. Add lore file:
   ```bash
   echo "Sylvia is a clever artificer..." > notes/sylvia_lore.txt
   ```

4. Activate character (change `"active": false` to `"active": true`)

### Adding a New LLM
1. Place model file in `model/` folder

2. Add to `characters.json`:
   ```json
   {
     "id": "neural_opus",
     "name": "Neural Opus 7B",
     "model_file": "model/neural-opus-7b.Q4_K_M.gguf",
     "active": true,
     "description": "Advanced reasoning model"
   }
   ```

## Memory Isolation

### Character → Separate Memory
- Kara's facts are stored in `memory/kara/summaries.json`
- Luna's facts are stored in `memory/luna/summaries.json`
- No cross-contamination

### Same Character + Different LLM → Shared Memory
```
Session 1: Kara + Dolphin
  → Learns fact about Drax
  → Stores in memory/kara/memory.json

Session 2: Kara + MythoMax
  → Loads same memory/kara/memory.json
  → Remembers fact about Drax
```

### Same Character + Same LLM → Continuous Memory
```
Session 1: Kara + Dolphin (Tuesday)
  → Conversation with user
  → Stores facts
  
Session 2: Kara + Dolphin (Wednesday)
  → Loads same memory from Tuesday
  → Continuous conversation
```

## File Structure Reference

```
my_local_ai/
├── characters.json                 ← Master character & LLM config
├── config.json                     ← Current session config
├── start.py                        ← Interactive launcher
│
├── scripts/
│   ├── run_llm.py                 ← Main chat loop (uses character-specific paths)
│   ├── update_memory.py           ← Digestion system (uses character-specific paths)
│   └── ...
│
├── memory/
│   ├── kara/
│   │   ├── memory.json            ← Kara's conversation history
│   │   ├── brain.json             ← Kara's persona
│   │   ├── faiss.index            ← Kara's semantic index
│   │   ├── summaries.json         ← Kara's facts
│   │   └── embeddings.npy         ← Kara's embeddings
│   │
│   ├── luna/
│   │   ├── memory.json
│   │   ├── brain.json
│   │   └── ...
│   │
│   └── iris/
│       ├── memory.json
│       └── ...
│
└── notes/
    ├── kara_verified_lore.txt
    ├── luna_lore.txt
    └── iris_lore.txt
```

## Implementation Details

### Path Resolution in run_llm.py
```python
# Character-specific paths
brain_path = os.path.join(project_root, "memory", character, "brain.json")
memory_path = os.path.join(project_root, "memory", character, "memory.json")

# Config paths with {character} placeholder
config["faiss_index"] = config["faiss_index"].format(character=character)
config["summaries_path"] = config["summaries_path"].format(character=character)
```

### Path Resolution in update_memory.py
```python
# Resolve character from config
character = cfg.get("current_character", "kara")

# Apply to paths
faiss_path = BASE / "memory" / character / "faiss.index"
summaries_path = BASE / "memory" / character / "summaries.json"
memory_path = BASE / "memory" / character / "memory.json"
```

## Testing

### Test 1: Character Isolation
```bash
# Session 1: Talk to Kara
python3 start.py
# Choose: Kara, Dolphin
# Ask: "Remember my name is Alex"
# Exit with Ctrl+C

# Session 2: Talk to Luna
python3 start.py
# Choose: Luna, Dolphin
# Ask: "What's my name?"
# Luna should NOT know "Alex" (different character, different memory)
```

### Test 2: LLM Flexibility
```bash
# Session 1: Kara + Dolphin
python3 start.py
# Choose: Kara, Dolphin
# Ask: "I like painting"
# Exit

# Session 2: Kara + MythoMax (same character, different LLM)
python3 start.py
# Choose: Kara, MythoMax
# Ask: "What did I say I like?"
# Kara should remember "painting" (shared memory)
```

## Architecture Benefits

1. **Character Authenticity**: Each character maintains its own identity and memory
2. **LLM Experimentation**: Test same character with different models
3. **Multi-User Scenarios**: Different characters can represent different personalities
4. **Memory Persistence**: All changes persist to character-specific folders
5. **Easy Expansion**: Add new characters/LLMs with simple config updates
6. **No Conflicts**: Zero risk of memory bleeding between characters

## Future Enhancements

- Character-LLM affinity: "Kara works best with MythoMax"
- Memory merge: Combine multiple characters' similar memories
- Character relationships: Luna remembers meeting Kara
- Configurable memory retention: How long to keep facts
- Per-character system prompts: Different instructions per character
