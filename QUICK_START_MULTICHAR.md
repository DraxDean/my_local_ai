# Multi-Character & Multi-LLM System - Quick Start

## ✅ What's Been Implemented

### 1. **Character Registry** (`characters.json`)
- **Kara** (active) - Spirit companion, memory in `memory/kara/`
- **Luna** (ready) - Mystical guide, memory folder created
- **Iris** (ready) - Analytical companion, memory folder created
- Easy to add more characters

### 2. **LLM Registry** (in `characters.json`)
- **Dolphin 2.9.3** (active) - Focused, conversational
- **MythoMax 13B** (active) - Creative, storytelling  
- **OpenHermes 2.5** (active) - Balanced, helpful

### 3. **Character-Specific Memory**
```
memory/
├─ kara/
│  ├─ memory.json       ← Kara's conversations
│  ├─ brain.json        ← Kara's persona
│  ├─ faiss.index       ← Kara's semantic index
│  ├─ summaries.json    ← Kara's learned facts
│  └─ embeddings.npy    ← Kara's embeddings
├─ luna/                ← Ready for Luna
└─ iris/                ← Ready for Iris
```

### 4. **Interactive Launcher** (`start.py`)
```bash
python3 start.py

# Then choose:
# 👤 SELECT CHARACTER: (Kara, Luna, Iris)
# 🤖 SELECT LLM MODEL: (Dolphin, MythoMax, OpenHermes)
```

### 5. **Automatic Path Resolution**
- Config uses placeholder: `memory/{character}/summaries.json`
- Automatically becomes: `memory/kara/summaries.json` when Kara is selected
- Same logic for LLM model selection

## 🔧 Updated Files

| File | Changes |
|------|---------|
| `characters.json` | NEW - Central character & LLM registry |
| `config.json` | Added `current_character`, `current_llm`, path placeholders |
| `start.py` | Rewrote - Interactive character + LLM selection |
| `scripts/run_llm.py` | Path resolution functions, character-aware loading |
| `scripts/update_memory.py` | Character-specific memory paths |
| `memory/kara/` | Migrated existing Kara memory here |
| `memory/luna/` | NEW - Ready for Luna |
| `memory/iris/` | NEW - Ready for Iris |

## 🧪 Verification

**Status**: ✅ All tests passing
- ✓ Character path substitution working
- ✓ Memory folders created
- ✓ All LLM models found
- ✓ Kara's lore file loaded
- ✓ Path resolution logic verified

## 📊 How Memory Works

### Scenario 1: Same Character, Same LLM
```
Session 1 (Tuesday):   Kara + Dolphin → learns facts → saves to memory/kara/
Session 2 (Wednesday): Kara + Dolphin → loads same memory/kara/ → remembers!
Result: Continuous conversation ✓
```

### Scenario 2: Same Character, Different LLM
```
Session 1 (Tuesday):   Kara + Dolphin → learns facts → saves to memory/kara/
Session 2 (Wednesday): Kara + MythoMax → loads same memory/kara/ → remembers!
Result: Same character with different model ✓
```

### Scenario 3: Different Characters
```
Session 1 (Tuesday):   Kara + Dolphin → learns facts → saves to memory/kara/
Session 2 (Wednesday): Luna + Dolphin → loads memory/luna/ (DIFFERENT) → no cross-talk
Result: Complete memory isolation ✓
```

## 🎮 Typical Workflow

### First Time
```bash
python3 start.py
  → Choose: Kara (1)
  → Choose: Dolphin (1)
  → Chat starts
  → Type: exit
```

### Second Time (Same Character & LLM)
```bash
python3 start.py
  → Choose: Kara (1)  [default, just press Enter]
  → Choose: Dolphin (1) [default, just press Enter]
  → Chat starts with Kara's existing memory
```

### Try Different LLM
```bash
python3 start.py
  → Choose: Kara (1)      [same character]
  → Choose: MythoMax (2)  [different LLM]
  → Chat starts with Kara's memory + MythoMax model
```

### Try Different Character
```bash
python3 start.py
  → Choose: Luna (2)      [different character]
  → Choose: Dolphin (1)   
  → Chat starts with Luna's memory (empty)
```

## 🚀 Next Steps

1. **Test it**: `python3 start.py` and try different combinations
2. **Add a character**: Update `characters.json` to activate Luna/Iris
3. **Compare outputs**: Talk to Kara, then Luna, see memory isolation
4. **Try LLMs**: Talk to Kara with different models, see consistency

## 📝 Adding a New Character

### Step 1: Update `characters.json`
```json
{
  "id": "sylvia",
  "name": "Sylvia",
  "description": "Clever artificer",
  "lore_file": "notes/sylvia_lore.txt",
  "memory_folder": "memory/sylvia",
  "active": true
}
```

### Step 2: Create memory folder
```bash
mkdir -p memory/sylvia
```

### Step 3: Add lore file
```bash
echo "Sylvia is..." > notes/sylvia_lore.txt
```

### Step 4: Reload start.py
```bash
python3 start.py  # Sylvia now shows in character list
```

## 🔑 Key Concepts

| Concept | Meaning |
|---------|---------|
| **Character** | Unique personality with separate memory (Kara, Luna, Iris) |
| **Isolated Memory** | Each character has own conversation history & facts |
| **LLM** | The model used for generation (Dolphin, MythoMax, OpenHermes) |
| **Path Placeholder** | `{character}` replaced with actual character name at runtime |
| **Lore File** | Character background in `notes/` |
| **Brain** | Persona data in `memory/{character}/brain.json` |

## 🐛 Troubleshooting

### "Path not found" errors
- Check that memory folder exists: `ls -la memory/kara/`
- Check characters.json matches folder names exactly

### Character memory not loading
- Verify `current_character` in config.json
- Check that `memory/{character}/memory.json` exists

### LLM model not found
- Check characters.json model_file path is correct
- Verify model file exists in model/ folder

## 📚 Full Documentation

See [MULTI_CHARACTER_MULTI_LLM.md](MULTI_CHARACTER_MULTI_LLM.md) for detailed technical documentation.
