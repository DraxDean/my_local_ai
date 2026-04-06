var express = require('express');
var router = express.Router();
var spawn = require('child_process').spawn;
var path = require('path');
var fs = require('fs');

/**
 * POST /api/chat - Send a message and get a response from the LLM
 * Body: { message: string, characterName: string (default: "Kara"), llmModel: string (default: "dolphin") }
 * Returns: { success: boolean, response: string, error: string }
 */
router.post('/', function(req, res, next) {
  const { message, characterName = 'kara', llmModel = 'dolphin' } = req.body;

  // Validate input
  if (!message || message.trim() === '') {
    return res.json({ 
      success: false, 
      error: 'Message cannot be empty' 
    });
  }

  // Update config with current character and LLM
  try {
    const configPath = path.join(__dirname, '..', 'config.json');
    const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    config.current_character = characterName;
    config.current_llm = llmModel;
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
  } catch (err) {
    console.error('Warning: Could not update config:', err.message);
  }

  // Build the input for the Python script (send message + exit to terminate cleanly)
  const chatInput = message + '\nexit\n';

  // Call the Python LLM script with unbuffered output
  // Python script will automatically use config.json to resolve paths and load the right LLM
  const pythonScript = spawn('python3', ['-u', 'scripts/run_llm.py'], {
    cwd: path.join(__dirname, '..'),
    env: { ...process.env, PYTHONUNBUFFERED: '1' }
  });

  let output = '';
  let errorOutput = '';
  let processError = null;
  let responseSent = false; // Prevent multiple responses

  // Handle stdout data
  pythonScript.stdout.on('data', (data) => {
    output += data.toString();
  });

  // Handle stderr data
  pythonScript.stderr.on('data', (data) => {
    errorOutput += data.toString();
  });

  // Handle process errors
  pythonScript.on('error', (err) => {
    processError = err;
  });

  // Helper function to safely send response only once
  const sendResponse = (data) => {
    if (!responseSent) {
      responseSent = true;
      console.log('[RESPONSE]', JSON.stringify(data));
      res.json(data);
    }
  };

  // Handle process exit
  pythonScript.on('close', (code) => {
    if (responseSent) return;
    
    if (processError) {
      return sendResponse({
        success: false,
        error: `Process error: ${processError.message}`
      });
    }

    if (code !== 0 && code !== null) {
      return sendResponse({
        success: false,
        error: `Process exited with code ${code}`
      });
    }

    // Clean output: remove carriage returns (from spinner)
    const lines = output.split('\n').map(line => line.replace(/\r/g, ''));

    let aiResponse = '';

    // Look for response text
    for (let i = 0; i < lines.length; i++) {
      let line = lines[i];
      
      // If line contains both "AI:" and response, extract just the response part
      if (line.includes('AI: ')) {
        const parts = line.split('AI: ');
        const afterAI = parts[parts.length - 1].trim();
        if (afterAI && afterAI.length > 5 && !afterAI.includes('Thinking')) {
          aiResponse = afterAI;
          break;
        }
      }

      // Otherwise look for response patterns on standalone lines
      line = line.trim();
      if (!line || line.includes('[info]') || line.includes('Local AI') || line === 'You:') {
        continue;
      }

      // Match response patterns
      if (line.startsWith('I am') || line.startsWith('I ')) {
        aiResponse = line;
        break;
      }

      // Match any natural language sentence (has common words and reasonable length)
      if (line.length > 10 && 
          !line.startsWith('##') && 
          !line.includes('[') &&
          /\b(I|you|your|this|that|my|can|will|have|are)\b/.test(line)) {
        aiResponse = line;
        break;
      }
    }

    if (!aiResponse) {
      return sendResponse({
        success: false,
        error: 'No response from AI'
      });
    }

    // Store this exchange in character-specific memory
    try {
      const characterPath = path.join(__dirname, '..', 'memory', characterName);
      
      // Ensure character memory directory exists
      if (!fs.existsSync(characterPath)) {
        fs.mkdirSync(characterPath, { recursive: true });
      }

      const memoryPath = path.join(characterPath, 'memory.json');
      let memory = { conversation_history: [] };
      if (fs.existsSync(memoryPath)) {
        memory = JSON.parse(fs.readFileSync(memoryPath, 'utf8'));
      }
      
      if (!memory.conversation_history) {
        memory.conversation_history = [];
      }
      
      memory.conversation_history.push({
        user: message,
        ai: aiResponse,
        timestamp: new Date().toISOString()
      });
      
      // Keep only last 50 exchanges to avoid file bloat
      if (memory.conversation_history.length > 50) {
        memory.conversation_history = memory.conversation_history.slice(-50);
      }
      
      fs.writeFileSync(memoryPath, JSON.stringify(memory, null, 2));
    } catch (err) {
      console.error('Warning: Could not save conversation to memory:', err.message);
    }

    sendResponse({
      success: true,
      response: aiResponse,
      characterName: characterName,
      llmModel: llmModel
    });
  });

  // Send input to the Python process
  pythonScript.stdin.write(chatInput);
  pythonScript.stdin.end();

  // Set a timeout in case the process hangs (45 seconds - generous for LLM response)
  const timeoutId = setTimeout(() => {
    if (pythonScript.exitCode === null && !responseSent) {
      pythonScript.kill('SIGTERM');
      sendResponse({
        success: false,
        error: 'Request timeout - LLM took too long to respond'
      });
    }
  }, 45000); // 45 second timeout
});

module.exports = router;
