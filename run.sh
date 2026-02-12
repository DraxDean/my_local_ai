#!/bin/bash
# Simple launcher for my_local_ai

set -e

# Activate virtual environment
source .venv/bin/activate

# Optional: Update memory (uncomment if needed)
# echo "Updating memory from notes..."
# python scripts/update_memory.py

# Start interactive model selector and chat
python start.py
