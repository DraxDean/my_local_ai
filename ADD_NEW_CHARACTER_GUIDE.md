# How to Add a New Character - Step by Step

This guide demonstrates how to add **Sylvia**, a new character, to the system.

## Step 1: Update `characters.json`

Find the `"characters"` array in `characters.json` and add a new entry:

```json
{
  "id": "sylvia",
  "name": "Sylvia",
  "description": "A clever artificer from the northern mountains",
  "lore_file": "notes/sylvia_lore.txt",
  "memory_folder": "memory/sylvia",
  "active": true
}
```

**Fields:**
- `id`: Short unique identifier (used in paths)
- `name`: Display name
- `description`: What player sees when selecting
- `lore_file`: Where character background is stored
- `memory_folder`: Where her memory will be saved
- `active`: Set to `true` to show in launcher

## Step 2: Create Memory Folder

```bash
mkdir -p /Users/draxlindgren/Downloads/my_local_ai/memory/sylvia
```

This creates the folder structure where Sylvia's data will be stored.

## Step 3: Create Lore File

Create `notes/sylvia_lore.txt` with her character description:

```
# Sylvia - The Northern Artificer

## Background
Sylvia is a clever artificer from the northern mountains, skilled in crafting and mechanical engineering. 

## Personality
- Direct and pragmatic
- Patient teacher
- Passionate about innovation
- Slightly skeptical of magic
- Values quality and precision

## Appearance
- Tall, with calloused hands
- Always carries a tool belt
- Sharp gray eyes
- Wears practical, durable clothing

## Relationship with the user
Sylvia has worked with the user on several projects. She respects their practical thinking and often collaborates on problem-solving.

## Key Facts
- Can craft almost anything from available materials
- Speaks with a slight northern accent
- Has encyclopedic knowledge of materials and methods
- Teaches through hands-on experience
- Prefers action to endless discussion
```

## Step 4: Reload start.py

That's it! Now when you run:

```bash
python3 start.py
```

Sylvia will appear in the character selection menu along with Kara, Luna, and Iris.

## Step 5: Test It

```bash
$ python3 start.py

🎮 Local AI Chat Interface
════════════════════════════════════════
👤 SELECT CHARACTER:
  1. Continue with Kara
  2. Luna - A mystical guide
  3. Iris - An analytical companion
  4. Sylvia - A clever artificer from the northern mountains  ← NEW!
  5. Exit

→ Choose: 4

🤖 SELECT LLM MODEL:
  1. Continue with Dolphin 2.9.3
  → Choose: 1

════════════════════════════════════════
👤 Character: Sylvia
🤖 Model: Dolphin 2.9.3
💾 Memory: memory/sylvia
════════════════════════════════════════

You: Hello Sylvia, what's your latest project?
Sylvia: I'm working on a precision locking mechanism for the vault...
```

## Advanced: Character with Multiple LLMs

Now if you run again and choose Sylvia with a different LLM:

```bash
$ python3 start.py
→ Character: 4 (Sylvia)
→ LLM: 2 (MythoMax)

════════════════════════════════════════
👤 Character: Sylvia
🤖 Model: MythoMax 13B
💾 Memory: memory/sylvia
════════════════════════════════════════

You: What was your latest project?
Sylvia: [Uses MythoMax model, but remembers her previous work from memory/sylvia/]
```

## File Structure After Adding Sylvia

```
characters.json
├─ kara (active)
├─ luna
├─ iris
└─ sylvia (NEW - active)

config.json
├─ current_character: "sylvia"  ← Updates when selected
└─ current_llm: "dolphin"

memory/
├─ kara/
│  └─ memory.json, brain.json, etc.
├─ luna/
├─ iris/
└─ sylvia/                      ← NEW folder
   ├─ memory.json              ← Created on first message
   ├─ brain.json               ← Created during digestion
   ├─ faiss.index
   ├─ summaries.json
   └─ embeddings.npy

notes/
├─ kara_verified_lore.txt
├─ luna_lore.txt
├─ iris_lore.txt
└─ sylvia_lore.txt              ← NEW lore file
```

## What Happens Behind the Scenes

When you select Sylvia:

1. **Path Substitution**: `memory/{character}/` becomes `memory/sylvia/`
2. **Config Update**: `config.json` updated with `"current_character": "sylvia"`
3. **Lore Loading**: `notes/sylvia_lore.txt` loaded for context
4. **Memory Check**: If `memory/sylvia/memory.json` exists, it loads; if not, creates new
5. **Chat Starts**: System uses Sylvia's memory (isolated from Kara's, Luna's, etc.)

## Removing a Character (Temporarily)

To hide a character without deleting data:

```json
{
  "id": "sylvia",
  "name": "Sylvia",
  ...
  "active": false  ← Change to false
}
```

Now Sylvia won't appear in the launcher, but her memory folder (`memory/sylvia/`) remains intact. When you re-enable her, all her memories come back.

## Permanently Removing a Character

To delete a character completely:

1. Remove entry from `characters.json`
2. Delete memory folder: `rm -rf memory/sylvia/`
3. Delete lore file: `rm notes/sylvia_lore.txt`

## Creating Characters from Existing Memory

If you have conversations with someone else's memory database:

1. Copy their memory folder to `memory/sylvia/`
2. Add Sylvia to `characters.json`
3. Create `notes/sylvia_lore.txt`
4. Sylvia now has their previous conversations!

## System Behavior When Adding Characters

| Action | Storage | Automatic? |
|--------|---------|-----------|
| Create memory folder | `memory/sylvia/` | ✓ Created on first use |
| Initialize memory.json | `memory/sylvia/memory.json` | ✓ Created on first message |
| Create brain.json | `memory/sylvia/brain.json` | ✓ Created during memory digestion |
| Build FAISS index | `memory/sylvia/faiss.index` | ✓ Auto-built from summaries |
| Generate embeddings | `memory/sylvia/embeddings.npy` | ✓ Auto-generated |

Once you add Sylvia to `characters.json` and create her folder, everything else happens automatically!

## Tips for Great Characters

### Diverse Personalities
- **Kara**: Stoic warrior, direct
- **Luna**: Mystical, poetic
- **Iris**: Analytical, logical
- **Sylvia**: Practical, hands-on

### Rich Lore Files
- Include background/history
- Define personality traits
- Explain relationship with user
- Add specific knowledge domains

### Consistent Memory
- Characters learn over time
- They remember previous conversations
- Their memories stay separate
- Switching LLMs keeps same memories

### Different Models
- **Dolphin**: Best for direct conversation
- **MythoMax**: Best for creative storytelling
- **OpenHermes**: Best for balanced/analytical

Pair character personality with appropriate LLM for best results:
- Sylvia (practical) + Dolphin (direct) = Great
- Luna (mystical) + MythoMax (creative) = Great
- Iris (analytical) + OpenHermes (balanced) = Great

## Troubleshooting

### "Character not appearing" 
Check:
1. Is `"active": true` in `characters.json`?
2. Did you save `characters.json`?
3. Is the syntax valid JSON?

### "Character has no memories"
Check:
1. Did you run conversation with that character?
2. Check if `memory/{character}/memory.json` exists
3. Run `system_status.py` to verify folder exists

### "Wrong model loading"
Check:
1. Is the model file path correct in `characters.json`?
2. Does the model file exist in the filesystem?
3. Run `test_multichar.py` to verify all models

## Next Characters to Consider

- 🗡️ **Kael** - Mysterious forge master
- 🌙 **Elowen** - Night guardian
- 💎 **Theron** - Gem merchant
- 🍃 **Vex** - Forest ranger
- ⚡ **Spark** - Lightning mage

Each can have unique personalities and knowledge domains!

---

**Summary**: Adding a character is just 3 steps:
1. Edit `characters.json` (add 1 entry)
2. Create memory folder (`mkdir`)
3. Create lore file (write description)

Everything else is automatic! 🚀
