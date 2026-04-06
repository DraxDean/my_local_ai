#!/usr/bin/env python3
"""
System status checker for multi-character AI system.
Shows available characters, LLMs, and memory status.
"""
import json
from pathlib import Path
from datetime import datetime

def get_file_stats(path):
    """Get file stats for display."""
    if not path.exists():
        return "✗ Missing", 0
    
    size = path.stat().st_size
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    
    if size > 1024 * 1024:
        size_str = f"{size / (1024*1024):.1f}MB"
    elif size > 1024:
        size_str = f"{size / 1024:.1f}KB"
    else:
        size_str = f"{size}B"
    
    return f"✓ {size_str}", mtime

def main():
    base = Path(__file__).parent
    config_path = base / "config.json"
    characters_path = base / "characters.json"
    
    print("\n🤖 Local AI System Status")
    print("=" * 80)
    
    # Load config
    with open(config_path) as f:
        config = json.load(f)
    
    with open(characters_path) as f:
        characters_data = json.load(f)
    
    # Current selections
    print(f"\n📍 Current Selection:")
    print(f"   Character: {config.get('current_character', 'kara')}")
    print(f"   LLM:       {config.get('current_llm', 'dolphin')}")
    
    # Available characters
    print(f"\n👥 Available Characters:")
    print("-" * 80)
    for char in characters_data["characters"]:
        status = "●" if char["active"] else "○"
        print(f"\n  {status} {char['name']} (ID: {char['id']})")
        print(f"     Description: {char['description']}")
        print(f"     Lore file: {char['lore_file']}")
        
        # Memory status
        memory_folder = base / char['memory_folder']
        print(f"     Memory folder: {memory_folder.name}/")
        
        if memory_folder.exists():
            memory_json = memory_folder / "memory.json"
            brain_json = memory_folder / "brain.json"
            faiss_index = memory_folder / "faiss.index"
            summaries = memory_folder / "summaries.json"
            embeddings = memory_folder / "embeddings.npy"
            
            files_status = []
            for fname, fpath in [
                ("memory.json", memory_json),
                ("brain.json", brain_json),
                ("faiss.index", faiss_index),
                ("summaries.json", summaries),
                ("embeddings.npy", embeddings),
            ]:
                status_str, mtime = get_file_stats(fpath)
                files_status.append(f"       {fname:15} {status_str}")
                if mtime and mtime != 0:
                    files_status[-1] += f" (updated: {mtime.strftime('%Y-%m-%d %H:%M')})"
            
            print("     Content:")
            print("\n".join(files_status))
        else:
            print(f"     ✗ Memory folder not found!")
    
    # Available LLMs
    print(f"\n\n🤖 Available LLM Models:")
    print("-" * 80)
    for llm in characters_data["llms"]:
        status = "●" if llm["active"] else "○"
        print(f"\n  {status} {llm['name']} (ID: {llm['id']})")
        print(f"     Description: {llm['description']}")
        print(f"     Model file: {llm['model_file']}")
        
        model_path = base / llm['model_file']
        status_str, _ = get_file_stats(model_path)
        print(f"     Status: {status_str}")
    
    # Overall stats
    print(f"\n\n📊 System Statistics:")
    print("-" * 80)
    
    total_memory = 0
    for char in characters_data["characters"]:
        memory_folder = base / char['memory_folder']
        if memory_folder.exists():
            for item in memory_folder.rglob('*'):
                if item.is_file():
                    total_memory += item.stat().st_size
    
    print(f"   Total character memory: {total_memory / (1024*1024):.1f} MB")
    print(f"   Characters defined: {len(characters_data['characters'])}")
    print(f"   LLMs available: {len(characters_data['llms'])}")
    print(f"   Active characters: {sum(1 for c in characters_data['characters'] if c['active'])}")
    print(f"   Active LLMs: {sum(1 for l in characters_data['llms'] if l['active'])}")
    
    print(f"\n  Config: {config_path}")
    print(f"  Characters: {characters_path}")
    
    print("\n" + "=" * 80)
    print("\n✅ Use 'python3 start.py' to begin a session\n")

if __name__ == "__main__":
    main()
