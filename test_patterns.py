#!/usr/bin/env python3
"""Test refined critique patterns."""

test_responses = [
    ("I am Kara, your sword spirit. I'm here for you, drax.", "ACCEPT"),
    ("Kara: Greetings, my wielder. What would you like me to do?", "ACCEPT"),
    ("Let's play a game of chess. Strategy is important.", "ACCEPT"),
    ("The Sword Spirit Battle Arena game features combat...", "REJECT"),
    ("You can download this game from the store", "REJECT"),
    ("## Features\n- Fast combat", "REJECT"),
    ("Kara: I shall shield you from all harm.", "ACCEPT"),
]

bad_patterns = [
    "## feature", "## gameplay", "## control", "## system", "## how to",
    "### game", "### feature",
    "download", "install", "platform", "console", "pc ", "mac ", "esrb",
    "game feature", "game play", "game mechanic", "game control", 
    "game download", "game stat", "this game", "the game feature",
    "action-adventure game", "hack-and-slash", "platformer game",
    "purchase", "achievement", "boss battle", "button", "click",
    "arrow key", "wasd", "mouse button",
    "lianna", "luna", "yuki",
    "as an ai", "i'm sorry, i can't", "how can i assist",
    "game rating", "game tag", "game category", "faq",
    "hours to complet", "total play time",
]

print("Testing refined patterns:\n")
passed = 0
for response, expected in test_responses:
    lower = response.lower()
    matched = None
    for pattern in bad_patterns:
        if pattern in lower:
            matched = pattern
            break
    
    result = "REJECT" if matched else "ACCEPT"
    status = "✓" if result == expected else "✗"
    if result == expected:
        passed += 1
    
    print(f"{status} {result:6} | {response[:40]}...")
    if matched:
        print(f"     Pattern: '{matched}'")

print(f"\nPassed: {passed}/{len(test_responses)}")
