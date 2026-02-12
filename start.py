#!/usr/bin/env python3
"""
Interactive model selector and launcher for my_local_ai chat interface.
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


def find_models(model_dir="model"):
    """Find all available model files in the model directory."""
    model_path = Path(model_dir)
    if not model_path.exists():
        return []
    
    # Look for common model file extensions
    extensions = [".gguf", ".bin", ".safetensors"]
    models = []
    
    for ext in extensions:
        models.extend(model_path.glob(f"*{ext}"))
    
    # Filter and group models
    models = sorted([m for m in models if m.is_file()])
    
    # Remove duplicate quantization levels - keep only Q4_K_M for mythomax
    filtered = []
    has_mythomax = False
    for model in models:
        if "mythomax" in model.name.lower():
            if "q4_k_m" in model.name.lower() and not has_mythomax:
                filtered.append(model)
                has_mythomax = True
            # Skip other mythomax quantization levels
        else:
            filtered.append(model)
    
    return filtered


def update_config(config_path, new_model_path):
    """Update the model_path in config.json."""
    with open(config_path) as f:
        config = json.load(f)
    
    config["model_path"] = str(new_model_path.absolute())
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)


def main():
    print("🤖 Local AI Model Selector")
    print("=" * 40)
    
    # Load current config
    config = load_config()
    current_model = Path(config["model_path"])
    
    # Find available models
    models = find_models()
    
    if not models:
        print("❌ No models found in 'model/' directory")
        print("   Place your .gguf, .bin, or .safetensors files there")
        sys.exit(1)
    
    # Display available models with "Last model" as option 1
    print("Available models:")
    print(f"  1. Use last model ({current_model.name}) [press Enter to use]")
    
    # Show other models
    option_num = 2
    model_map = {}  # Map option number to model path
    for model in models:
        if model.name != current_model.name:
            model_map[option_num] = model
            print(f"  {option_num}. {model.name}")
            option_num += 1
    
    print(f"  {option_num}. Exit")
    print()
    
    # Get user choice (default to option 1 if just pressing Enter)
    while True:
        try:
            choice = input("Select model (number) [default 1]: ").strip()
            
            # Default to 1 (last model) if empty input
            if not choice:
                choice = "1"
            
            choice_num = int(choice)
            
            if choice_num == 1:  # Use last model
                break
            elif choice_num == option_num:  # Exit
                print("Goodbye! 👋")
                sys.exit(0)
            elif choice_num in model_map:  # Select specific model
                selected_model = model_map[choice_num]
                print(f"Switching to: {selected_model.name}")
                update_config("config.json", selected_model)
                break
            else:
                print(f"❌ Please enter a number between 1 and {option_num}")
                
        except (ValueError, KeyboardInterrupt):
            print("\nGoodbye! 👋")
            sys.exit(0)
    
    # Launch the chat interface
    # Reload config to get the updated model path
    updated_config = load_config()
    print(f"\n🚀 Starting chat with {Path(updated_config['model_path']).name}")
    print("=" * 40)
    
    try:
        subprocess.run([sys.executable, "scripts/run_llm.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error launching chat interface: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nChat session ended.")


if __name__ == "__main__":
    main()