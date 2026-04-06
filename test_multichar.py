#!/usr/bin/env python3
"""
Test script to verify path resolution for multi-character system.
"""
import json
from pathlib import Path

def test_path_resolution():
    """Test that character paths resolve correctly."""
    base = Path(__file__).parent
    
    # Load config
    with open(base / "config.json") as f:
        config = json.load(f)
    
    # Load characters
    with open(base / "characters.json") as f:
        characters_data = json.load(f)
    
    print("🧪 Testing Multi-Character Path Resolution\n")
    print("=" * 60)
    
    # Test 1: Character substitution
    print("\n✓ Test 1: Character Path Substitution")
    for char in characters_data["characters"]:
        if not char["active"]:
            continue
        
        character = char["id"]
        test_config = config.copy()
        
        # Resolve paths
        for path_key in ["faiss_index", "summaries_path", "embeddings_npy"]:
            if path_key in test_config:
                test_config[path_key] = test_config[path_key].format(character=character)
        
        print(f"\n  Character: {char['name']} (id='{character}')")
        print(f"    FAISS:     {test_config['faiss_index']}")
        print(f"    Summaries: {test_config['summaries_path']}")
        print(f"    Embeddings: {test_config['embeddings_npy']}")
        
        # Check that folders exist
        memory_folder = base / "memory" / character
        if memory_folder.exists():
            print(f"    ✓ Memory folder exists: {memory_folder}")
        else:
            print(f"    ✗ Memory folder missing: {memory_folder}")
    
    # Test 2: LLM resolution
    print("\n\n✓ Test 2: LLM Model Resolution")
    for llm in characters_data["llms"]:
        if not llm["active"]:
            continue
        
        print(f"\n  LLM: {llm['name']} (id='{llm['id']}')")
        print(f"    Model: {llm['model_file']}")
        
        model_path = base / llm['model_file']
        if model_path.exists():
            size_mb = model_path.stat().st_size / (1024 * 1024)
            print(f"    ✓ Model exists ({size_mb:.1f} MB)")
        else:
            print(f"    ✗ Model missing: {model_path}")
    
    # Test 3: Character lore files
    print("\n\n✓ Test 3: Character Lore Files")
    for char in characters_data["characters"]:
        if not char["active"]:
            continue
        
        print(f"\n  Character: {char['name']}")
        lore_path = base / char['lore_file']
        if lore_path.exists():
            file_size = lore_path.stat().st_size
            print(f"    ✓ Lore file exists ({file_size} bytes): {lore_path}")
        else:
            print(f"    ✗ Lore file missing: {lore_path}")
    
    print("\n" + "=" * 60)
    print("\n✅ Path resolution test complete!\n")

if __name__ == "__main__":
    test_path_resolution()
