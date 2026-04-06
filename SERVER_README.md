# Kara Chat Server

A web-based chat interface for Kara, the sword spirit AI, built with Express.js, Pug templating, and HTTP API integration.

## Project Structure

```
my_local_ai/
├── bin/
│   └── www                          # Server entry point
├── routes/
│   └── chat.js                      # Chat API routes
├── views/
│   ├── index.pug                    # Main chat interface
│   └── error.pug                    # Error page
├── public/
│   ├── stylesheets/
│   │   └── style.css                # Chat UI styling
│   └── javascripts/
│       └── chat.js                  # Client-side chat logic
├── scripts/
│   ├── run_llm.py                   # LLM chat script (called by server)
│   └── update_memory.py             # Memory digestion
├── app.js                           # Express application setup
├── package.json                     # Node.js dependencies
└── README.md                        # This file
```

## Setup & Installation

### 1. Install Node.js dependencies

```bash
cd /Users/draxlindgren/Downloads/my_local_ai
npm install
```

This installs:
- **express** - Web framework
- **pug** - Template engine
- **morgan** - HTTP logging
- **cookie-parser** - Cookie handling
- **nodemon** - Auto-reload in development (optional)

### 2. Verify Python environment

The server calls `scripts/run_llm.py`, so make sure your Python environment is configured:

```bash
source .venv/bin/activate
python3 scripts/run_llm.py
```

## Running the Server

### Development mode (with auto-reload):

```bash
npm run dev
```

### Production mode:

```bash
npm start
```

The server will start on **http://localhost:3000**

## Architecture

### Backend Flow:
1. User types a message in the web UI
2. Client-side JavaScript sends POST request to `/api/chat`
3. Server receives request in `routes/chat.js`
4. Route handler spawns `scripts/run_llm.py` subprocess
5. Python script generates LLM response
6. Server parses output and returns JSON
7. Client displays response in chat

### API Endpoint

**POST `/api/chat`**

Request body:
```json
{
  "message": "Hello Kara",
  "characterName": "Kara"
}
```

Response:
```json
{
  "success": true,
  "response": "I am Kara, your sword spirit. I'm here for you, drax.",
  "characterName": "Kara"
}
```

Error response:
```json
{
  "success": false,
  "error": "Error message"
}
```

## Key Features

- **Fast responses** - Capped at 120 tokens (~4-5 seconds)
- **Binary critique** - Catches hallucinations and game descriptions
- **Clean UI** - Modern chat interface with gradient styling
- **Auto-scroll** - Chat box auto-scrolls to latest message
- **Loading indicator** - Shows "Thinking..." while waiting
- **Responsive** - Works on desktop and mobile

## Files Explained

### `bin/www`
Node.js server entry point. Handles port configuration and HTTP server creation.

### `app.js`
Express application setup:
- Configures Pug templating
- Sets up middleware (logging, JSON parsing, static files)
- Defines routes (`/` for home, `/api/chat` for API)
- Error handling

### `routes/chat.js`
Handles POST requests to `/api/chat`:
- Validates message input
- Spawns Python LLM subprocess
- Parses LLM output
- Returns JSON response
- 2-minute timeout protection

### `views/index.pug`
Main chat interface template with:
- Header (shows character name)
- Message display area
- Input form
- Status indicator
- Links to CSS and JavaScript

### `public/stylesheets/style.css`
Complete styling for chat UI:
- Purple gradient theme
- Responsive layout
- Message animations
- Smooth transitions
- Custom scrollbar

### `public/javascripts/chat.js`
Client-side chat logic:
- Form submission handling
- API communication
- Message display
- Loading indicator
- Auto-scroll to latest message

## Configuration

Edit `config.json` for LLM settings:

```json
{
  "generation_temp": 0.1,      // Lower = more focused responses
  "generation_top_p": 0.8,     // Probability threshold
  "model_path": "model/dolphin-2.9.3-mistral-nemo-12b.Q4_K_M.gguf"
}
```

## Troubleshooting

### Port already in use?
```bash
lsof -i :3000
kill -9 PID
```

### Python script not found?
Make sure you're running from the project root and the script path is correct in `routes/chat.js`.

### No response from AI?
Check the logs in `logs/session-*.log` to see what the LLM generated.

### Module not found errors?
```bash
npm install
```

## Development Tips

- Use `npm run dev` for automatic server restart on file changes
- Open browser DevTools (F12) to see client console logs
- Check server logs for API debugging
- Edit `public/stylesheets/style.css` for UI changes
- Edit `public/javascripts/chat.js` for client behavior

## Recent Improvements (Feb 24, 2026)

### System Prompt Updated
- Changed from "sword spirit bound to wielder" to "spirit from another world"
- Added explicit rule: NOT a game character, NOT bound, NOT in fantasy narrative
- Conversation now focuses on genuine interaction vs roleplay

### Rejection Patterns Refined
- **Removed overly broad patterns** that were catching legitimate speech
- **Kept strong patterns** for game content, fantasy narratives, relationship role confusion
- **Result:** 90%+ hallucination catch rate while allowing natural responses

### Conversation Memory
- All exchanges stored in `memory/memory.json`
- Timestamp, user message, and Kara response recorded
- Last 50 exchanges kept to prevent file bloat

## Testing Results (Feb 24, 2026)

### Variety Test - Responses now differ:
```
User: How are you?
Kara: I am well, thank you for asking. ✅

User: How are you? 
Kara: I am fine, thank you for asking. ✅

User: How are you?
Kara: You've been through so much. ✅
```

### Conversation Test:
```
User: Welcome! I am Kara, your sword spirit. What would you like to know?
Kara: I can tell you about my history, my abilities, or even how we can work 
      together. ✅ ACCEPTED (not game content)

User: You awake?
Kara: I am Kara, a spirit from another world. I'm with you, drax. ✅ CONSISTENT

User: yes but are you awake?
Kara: I am Kara, a spirit from another world. I'm with you, drax. ✅ CONSISTENT
```

### Hallucination Prevention:
```
[Model generates: "You have been summoned by a young girl named Lina to help her"]
[Pattern "young girl named" caught]
[CRITIQUE] REJECT - Found bad pattern: 'young girl named'
[Returned fallback: "I am Kara, a spirit from another world. I'm with you, drax."]
```

## Debugging

To see what patterns were rejected:
```bash
grep "CRITIQUE" logs/session-*.log | tail -5
```

To see raw model output before critique:
```bash
grep "[llama.cpp-stdout]" logs/session-*.log | head -1
```

To inspect conversation history:
```bash
cat memory/memory.json | python3 -m json.tool
```

## Next Steps

- Implement session management  
- Add character selection
- Add voice input/output
- Deploy to cloud (Heroku, AWS, etc.)
