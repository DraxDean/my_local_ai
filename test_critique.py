#!/usr/bin/env python3
"""Test the critique function directly."""
import sys
import os

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

# Import the critique function
from run_llm import self_critique_response

test_cases = [
    # (input, expected_action, name)
    ("I am kara, your sword spirit. I'm here for you, drax.", "ACCEPT", "Clean response"),
    ("# Sword Spirit Battle Arena - Download Now! ## Features - Attack...", "REJECT", "Game description"),  
    ("Kara: The game features arcade gameplay with click to attack controls", "REJECT", "Game features"),
    ("Luna appears and says hello to you there", "REJECT", "Luna reference"),
    ("I am Kara. Let me help you, Drax.", "ACCEPT", "Simple authentic"),
    ("Click the left mouse button to strike. Arrow keys move. Press ESRB", "REJECT", "Controls/rating"),
    ("You can download this game and install it on PC or Mac", "REJECT", "Download/install"),
]

print("Testing self_critique_response():\n")
for response, expected, desc in test_cases:
    result = self_critique_response(response, "test query", "Kara")
    
    if expected == "ACCEPT":
        if result == response:
            print(f"✓ {desc}")
            print(f"  Input: {response[:50]}...")
            print(f"  Action: ACCEPTED\n")
        else:
            print(f"✗ {desc}")
            print(f"  Expected: ACCEPT (unchanged)")
            print(f"  Got: {result[:50]}...\n")
    else:  # REJECT
        if "I am Kara, your sword spirit" in result:
            print(f"✓ {desc}")
            print(f"  Input: {response[:50]}...")
            print(f"  Action: REJECTED → {result}\n")
        else:
            print(f"✗ {desc}")
            print(f"  Expected: REJECT with authentic response")
            print(f"  Got: {result[:50]}...\n")
