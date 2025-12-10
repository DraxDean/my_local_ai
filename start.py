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
    
    return sorted([m for m in models if m.is_file()])


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
    
    # Display current model
    print(f"Current model: {current_model.name}")
    print()
    
    # Display available models
    print("Available models:")
    for i, model in enumerate(models, 1):
        marker = " ✓" if model.name == current_model.name else ""
        print(f"  {i}. {model.name}{marker}")
    
    print(f"  {len(models) + 1}. Start with current model")
    print(f"  {len(models) + 2}. Exit")
    print()
    
    # Get user choice
    while True:
        try:
            choice = input("Select model (number): ").strip()
            if not choice:
                continue
                
            choice_num = int(choice)
            
            if choice_num == len(models) + 2:  # Exit
                print("Goodbye! 👋")
                sys.exit(0)
            elif choice_num == len(models) + 1:  # Start with current
                break
            elif 1 <= choice_num <= len(models):  # Select specific model
                selected_model = models[choice_num - 1]
                if selected_model.name != current_model.name:
                    print(f"Switching to: {selected_model.name}")
                    update_config("config.json", selected_model)
                break
            else:
                print(f"❌ Please enter a number between 1 and {len(models) + 2}")
                
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