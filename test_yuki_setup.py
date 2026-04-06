#!/usr/bin/env python3
"""Quick test to verify Yuki character loads correctly"""
import json
import os

# Check if Yuki's memory has the correct ai_name
yuki_memory_path = "memory/yuki/memory.json"
if os.path.exists(yuki_memory_path):
    with open(yuki_memory_path) as f:
        yuki_mem = json.load(f)
    print(f"✓ Yuki memory.json exists")
    print(f"  - ai_name: {yuki_mem.get('ai_name', 'MISSING')}")
    print(f"  - user_name: {yuki_mem.get('user_name', 'MISSING')}")
    print(f"  - important_facts: {len(yuki_mem.get('important_facts', []))} facts")
else:
    print("✗ Yuki memory.json NOT FOUND")

# Check if Yuki's brain.json exists
yuki_brain_path = "memory/yuki/brain.json"
if os.path.exists(yuki_brain_path):
    with open(yuki_brain_path) as f:
        yuki_brain = json.load(f)
    print(f"✓ Yuki brain.json exists")
    print(f"  - character_profile: {bool(yuki_brain.get('character_profile'))}")
    print(f"  - communication_style: {bool(yuki_brain.get('communication_style'))}")
else:
    print("✗ Yuki brain.json NOT FOUND")

# Check if Yuki's lore file exists
yuki_lore_path = "yuki_verified_lore.txt"
if os.path.exists(yuki_lore_path):
    with open(yuki_lore_path) as f:
        lore = f.read()
    print(f"✓ Yuki lore file exists ({len(lore)} bytes)")
    print(f"  - Contains 'Yuki': {'Yuki' in lore}")
    print(f"  - Contains 'sword spirit': {'sword spirit' in lore}")
    print(f"  - Contains 'Drax': {'Drax' in lore}")
else:
    print("✗ Yuki lore file NOT FOUND")

# Check characters.json
with open("characters.json") as f:
    chars = json.load(f)
yuki_char = next((c for c in chars['characters'] if c['id'] == 'yuki'), None)
if yuki_char:
    print(f"✓ Yuki in characters.json")
    print(f"  - name: {yuki_char.get('name')}")
    print(f"  - lore_file: {yuki_char.get('lore_file')}")
    print(f"  - active: {yuki_char.get('active')}")
else:
    print("✗ Yuki NOT in characters.json")

print("\nAll checks complete!")
