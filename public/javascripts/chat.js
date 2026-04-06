/**
 * Chat Client - Handles UI interactions and API communication
 */

const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');
const messagesContainer = document.getElementById('messages');
const statusDiv = document.getElementById('status');
const characterNameEl = document.getElementById('characterName');
const characterSelect = document.getElementById('characterSelect');
const llmSelect = document.getElementById('llmSelect');

// State
let currentCharacter = 'kara';
let currentLLM = 'dolphin';

/**
 * Load available characters and LLMs from server
 */
async function loadConfig() {
  try {
    const response = await fetch('/api/config');
    const data = await response.json();
    
    if (data.characters) {
      characterSelect.innerHTML = '';
      data.characters.forEach(char => {
        const option = document.createElement('option');
        option.value = char.id;
        option.textContent = char.name;
        characterSelect.appendChild(option);
      });
      characterSelect.value = data.current_character || 'kara';
      currentCharacter = data.current_character || 'kara';
    }
    
    if (data.llms) {
      llmSelect.innerHTML = '';
      data.llms.forEach(llm => {
        const option = document.createElement('option');
        option.value = llm.id;
        option.textContent = llm.name;
        llmSelect.appendChild(option);
      });
      llmSelect.value = data.current_llm || 'dolphin';
      currentLLM = data.current_llm || 'dolphin';
    }
    
    updateCharacterDisplay();
  } catch (error) {
    console.error('Failed to load config:', error);
  }
}

/**
 * Update character display name in header
 */
function updateCharacterDisplay() {
  const charOption = characterSelect.querySelector(`option[value="${currentCharacter}"]`);
  if (charOption) {
    characterNameEl.textContent = charOption.textContent;
  }
}

/**
 * Handle character selection change
 */
characterSelect.addEventListener('change', (e) => {
  currentCharacter = e.target.value;
  updateCharacterDisplay();
  
  // Clear messages when switching characters
  messagesContainer.innerHTML = `
    <div class="message system">
      <span>Switched to ${characterSelect.options[characterSelect.selectedIndex].text}. What would you like to know?</span>
    </div>
  `;
});

/**
 * Handle LLM selection change
 */
llmSelect.addEventListener('change', (e) => {
  currentLLM = e.target.value;
  
  // Show notification
  const llmName = llmSelect.options[llmSelect.selectedIndex].text;
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message system';
  const span = document.createElement('span');
  span.textContent = `Switched to ${llmName} model.`;
  messageDiv.appendChild(span);
  messagesContainer.appendChild(messageDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
});

/**
 * Add a message to the chat display
 */
function addMessage(text, type = 'ai') {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${type}`;
  
  const span = document.createElement('span');
  span.textContent = text;
  
  messageDiv.appendChild(span);
  messagesContainer.appendChild(messageDiv);
  
  // Auto-scroll to bottom
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * Show loading indicator
 */
function showLoading(show = true) {
  if (show) {
    statusDiv.style.display = 'block';
  } else {
    statusDiv.style.display = 'none';
  }
}

/**
 * Disable send button
 */
function setSendButtonState(enabled = true) {
  sendButton.disabled = !enabled;
  sendButton.textContent = enabled ? 'Send' : 'Sending...';
}

/**
 * Send message to the server API
 */
async function sendMessage(message) {
  try {
    setSendButtonState(false);
    showLoading(true);
    
    // Add user message to chat
    addMessage(message, 'user');
    userInput.value = '';
    
    // Send to API
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: message,
        characterName: currentCharacter,
        llmModel: currentLLM
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      // Add AI response to chat
      addMessage(data.response, 'ai');
    } else {
      // Add error message
      addMessage(`Error: ${data.error || 'Unknown error'}`, 'ai');
    }
  } catch (error) {
    console.error('Error:', error);
    addMessage(`Connection error: ${error.message}`, 'ai');
  } finally {
    setSendButtonState(true);
    showLoading(false);
    userInput.focus();
  }
}

/**
 * Handle form submission
 */
chatForm.addEventListener('submit', (e) => {
  e.preventDefault();
  
  const message = userInput.value.trim();
  if (message) {
    sendMessage(message);
  }
});

/**
 * Optional: Allow Shift+Enter for multi-line input
 */
userInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    chatForm.dispatchEvent(new Event('submit'));
  }
});

/**
 * Initialize on page load
 */
window.addEventListener('load', () => {
  loadConfig();
  userInput.focus();
});
