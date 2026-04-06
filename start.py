#!/usr/bin/env python3
"""
Interactive character and model selector for my_local_ai chat interface.
Allows selection of different character cards and LLM models.
"""
import json
import os
import subprocess
import sys
from pathlib import Path


def load_config():
    """Load configuration from config.json."""
    config_path = Path("config.json")
    if not config_path.exists():
        print("❌ Error: config.json not found")
        sys.exit(1)
    
    with open(config_path) as f:
        return json.load(f)


def load_characters():
    """Load character and LLM definitions."""
    char_path = Path("characters.json")
    if not char_path.exists():
        print("❌ Error: characters.json not found")
        sys.exit(1)
    
    with open(char_path) as f:
        return json.load(f)


def update_config(config_path, character_id, llm_id):
    """Update the character and model selection in config.json."""
    with open(config_path) as f:
        config = json.load(f)
    
    config["current_character"] = character_id
    config["current_llm"] = llm_id
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)


def select_character(characters_data, current_char):
    """Interactive character selection."""
    active_chars = [c for c in characters_data["characters"] if c["active"]]
    
    print("\n👤 SELECT CHARACTER:")
    print("=" * 40)
    
    # Show active characters with current as option 1
    current_name = next((c["name"] for c in characters_data["characters"] 
                        if c["id"] == current_char), None)
    
    print(f"  1. Continue with {current_name} [press Enter to use]")
    
    char_map = {}
    option_num = 2
    for char in active_chars:
        if char["id"] != current_char:
            char_map[option_num] = char["id"]
            print(f"  {option_num}. {char['name']} - {char['description']}")
            option_num += 1
    
    print(f"  {option_num}. Exit")
    print()
    
    while True:
        try:
            choice = input("Select character (number) [default 1]: ").strip()
            
            if not choice:
                choice = "1"
            
            choice_num = int(choice)
            
            if choice_num == 1:  # Use current character
                return current_char
            elif choice_num == option_num:  # Exit
                print("Goodbye! 👋")
                sys.exit(0)
            elif choice_num in char_map:  # Select specific character
                selected_char = char_map[choice_num]
                selected_name = next(c["name"] for c in characters_data["characters"] 
                                   if c["id"] == selected_char)
                print(f"✓ Switched to: {selected_name}")
                return selected_char
            else:
                print(f"❌ Please enter a number between 1 and {option_num}")
                
        except (ValueError, KeyboardInterrupt):
            print("\nGoodbye! 👋")
            sys.exit(0)


def select_llm(characters_data, current_llm):
    """Interactive LLM selection."""
    active_llms = [l for l in characters_data["llms"] if l["active"]]
    
    print("\n🤖 SELECT LLM MODEL:")
    print("=" * 40)
    
    # Show active LLMs with current as option 1
    current_name = next((l["name"] for l in characters_data["llms"] 
                        if l["id"] == current_llm), None)
    
    print(f"  1. Continue with {current_name} [press Enter to use]")
    
    llm_map = {}
    option_num = 2
    for llm in active_llms:
        if llm["id"] != current_llm:
            llm_map[option_num] = llm["id"]
            print(f"  {option_num}. {llm['name']}")
            print(f"      └─ {llm['description']}")
            option_num += 1
    
    print(f"  {option_num}. Exit")
    print()
    
    while True:
        try:
            choice = input("Select LLM (number) [default 1]: ").strip()
            
            if not choice:
                choice = "1"
            
            choice_num = int(choice)
            
            if choice_num == 1:  # Use current model
                return current_llm
            elif choice_num == option_num:  # Exit
                print("Goodbye! 👋")
                sys.exit(0)
            elif choice_num in llm_map:  # Select specific model
                selected_llm = llm_map[choice_num]
                selected_name = next(l["name"] for l in characters_data["llms"] 
                                   if l["id"] == selected_llm)
                print(f"✓ Switched to: {selected_name}")
                return selected_llm
            else:
                print(f"❌ Please enter a number between 1 and {option_num}")
                
        except (ValueError, KeyboardInterrupt):
            print("\nGoodbye! 👋")
            sys.exit(0)


def main():
    print("🎮 Local AI Chat Interface")
    print("=" * 40)
    
    # Load current config and character data
    config = load_config()
    characters_data = load_characters()
    
    # Get current selections
    current_character = config.get("current_character", "kara")
    current_llm = config.get("current_llm", "dolphin")
    
    # Interactive selection
    selected_character = select_character(characters_data, current_character)
    selected_llm = select_llm(characters_data, current_llm)
    
    # Update config with selections
    update_config("config.json", selected_character, selected_llm)
    
    # Get character and LLM details
    char_info = next((c for c in characters_data["characters"] 
                     if c["id"] == selected_character), None)
    llm_info = next((l for l in characters_data["llms"] 
                    if l["id"] == selected_llm), None)
    
    print()
    print("=" * 40)
    print(f"👤 Character: {char_info['name']}")
    print(f"🤖 Model: {llm_info['name']}")
    print(f"💾 Memory: {char_info['memory_folder']}")
    print("=" * 40)
    print()
    
    # Launch the chat interface
    try:
        subprocess.run([sys.executable, "scripts/run_llm.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error launching chat interface: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nChat session ended.")


if __name__ == "__main__":
    main()