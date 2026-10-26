/**
 * Smart FAQ Assistant - Chatbot Interface Logic
 * Handles real-time messaging, category filtering, feedback reporting,
 * typing indicators, loading states, empty state cards, error recovery,
 * answer copying, and sessionStorage persistence.
 */

document.addEventListener('DOMContentLoaded', () => {
  const chatMessages = document.getElementById('chat-messages');
  const chatForm = document.getElementById('chat-form');
  const chatInput = document.getElementById('chat-input');
  const chatInputClear = document.getElementById('chat-input-clear');
  const chatSendBtn = document.getElementById('chat-send-btn');
  const chatSendText = document.getElementById('chat-send-text');
  const chatSendIcon = document.getElementById('chat-send-icon');
  const categoryPills = document.querySelectorAll('.category-pill');
  const activeCategoryBadge = document.getElementById('active-category-badge');
  const clearChatBtn = document.getElementById('clear-chat-btn');

  // Mobile sidebar drawer elements
  const chatSidebarToggle = document.getElementById('chat-sidebar-toggle');
  const chatSidebarClose = document.getElementById('chat-sidebar-close');
  const chatSidebar = document.getElementById('chat-sidebar');
  const chatSidebarBackdrop = document.getElementById('chat-sidebar-backdrop');

  let currentCategory = window.INITIAL_CATEGORY || '';
  let lastFailedQuery = null;

  // Initialize Mobile Chat Sidebar Drawer
  initChatSidebarDrawer();

  // Restore chat messages from sessionStorage
  restoreChatSession();

  // If initial query passed via URL params (e.g. from Home search or FAQ directory "Ask in Chat")
  if (window.INITIAL_QUERY && window.INITIAL_QUERY.trim() !== '') {
    sendMessage(window.INITIAL_QUERY);
  }

  // Handle Input typing for clear (X) icon
  if (chatInput && chatInputClear) {
    chatInput.addEventListener('input', () => {
      if (chatInput.value.trim().length > 0) {
        chatInputClear.classList.add('visible');
      } else {
        chatInputClear.classList.remove('visible');
      }
    });

    chatInputClear.addEventListener('click', () => {
      chatInput.value = '';
      chatInputClear.classList.remove('visible');
      chatInput.focus();
    });
  }

  // Handle Category selection
  function setCategory(cat) {
    currentCategory = cat || '';
    categoryPills.forEach(pill => {
      pill.classList.toggle('active', (pill.getAttribute('data-category') || '') === currentCategory);
    });
    if (activeCategoryBadge) {
      activeCategoryBadge.textContent = currentCategory ? `Filtered: ${currentCategory}` : 'All Categories';
    }
  }

  categoryPills.forEach(pill => {
    pill.addEventListener('click', () => {
      const cat = pill.getAttribute('data-category') || '';
      setCategory(cat);
      // If mobile drawer open, close it after selection
      closeChatSidebarDrawer();
    });
  });

  // Global hooks for SPA section switching and external trigger actions
  window.sendChatMessage = function(queryText, cat) {
    if (cat !== undefined) {
      setCategory(cat);
    }
    if (queryText && queryText.trim() !== '') {
      sendMessage(queryText.trim());
    }
  };

  window.setChatCategory = function(cat) {
    setCategory(cat);
  };

  // Handle Clear Chat
  if (clearChatBtn) {
    clearChatBtn.addEventListener('click', () => {
      if (confirm('Clear the current conversation history?')) {
        sessionStorage.removeItem('sfaq_chat_history');
        chatMessages.innerHTML = '';
        renderEmptyState();
      }
    });
  }

  // Handle form submission
  if (chatForm) {
    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const query = chatInput.value.trim();
      if (!query) return;

      chatInput.value = '';
      if (chatInputClear) chatInputClear.classList.remove('visible');
      sendMessage(query);
    });
  }

  // Delegated click handler for suggestion chips, feedback, copy, and retry buttons
  chatMessages.addEventListener('click', (e) => {
    // 1. Suggestion Chip or Welcome Prompt Click
    const promptBtn = e.target.closest('.chip, .welcome-prompt-btn');
    if (promptBtn) {
      const qText = promptBtn.getAttribute('data-question') || promptBtn.querySelector('span:last-child')?.textContent || promptBtn.textContent.trim();
      if (qText) {
        sendMessage(qText);
      }
      return;
    }

    // 2. Feedback Button Click (Thumbs Up / Down)
    const feedbackBtn = e.target.closest('.btn-feedback');
    if (feedbackBtn) {
      const logId = feedbackBtn.getAttribute('data-log-id');
      const val = feedbackBtn.getAttribute('data-value');
      const parent = feedbackBtn.closest('.feedback-actions');

      if (!logId || !val || feedbackBtn.disabled) return;
      submitFeedback(logId, val, parent);
      return;
    }

    // 3. Copy Answer Button Click
    const copyBtn = e.target.closest('.btn-copy');
    if (copyBtn) {
      const textToCopy = copyBtn.getAttribute('data-answer');
      if (textToCopy) {
        navigator.clipboard.writeText(textToCopy).then(() => {
          copyBtn.classList.add('copied');
          copyBtn.innerHTML = `✓ Copied!`;
          setTimeout(() => {
            copyBtn.classList.remove('copied');
            copyBtn.innerHTML = `📋 Copy`;
          }, 2000);
        }).catch(err => {
          console.warn('Clipboard write failed:', err);
        });
      }
      return;
    }

    // 4. Retry Failed Message Button Click
    const retryBtn = e.target.closest('.btn-retry-query');
    if (retryBtn && lastFailedQuery) {
      const errorCard = retryBtn.closest('.message-row');
      if (errorCard) errorCard.remove();
      sendMessage(lastFailedQuery);
    }
  });

  // Core Send Message Function with Loading States & Error Handling
  async function sendMessage(userText) {
    if (!userText || userText.trim() === '') return;
    userText = userText.trim();
    lastFailedQuery = userText;

    // Record into session history for Home Dashboard
    if (window.addSessionRecentQuery) {
      window.addSessionRecentQuery(userText);
    }

    // Remove empty state if present
    const emptyState = document.getElementById('chat-empty-state');
    if (emptyState) emptyState.remove();

    // 1. Append user message bubble
    appendMessage({
      sender: 'user',
      text: userText,
      time: getCurrentTime()
    });

    // 2. Set Loading State: disable input & turn send button into spinner
    setLoadingState(true);

    // 3. Show typing indicator
    const typingId = showTypingIndicator();

    try {
      // 4. Call backend AI Agent API
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: userText,
          category: currentCategory
        })
      });

      if (!res.ok) {
        throw new Error(`HTTP error ${res.status}`);
      }

      const data = await res.json();
      removeTypingIndicator(typingId);
      setLoadingState(false);

      // 5. Render Bot Response
      appendMessage({
        sender: 'bot',
        text: data.answer,
        status: data.status,
        confidence: data.confidence_percent,
        category: data.detected_category,
        matchedFaq: data.matched_faq,
        suggestions: data.suggested_questions || [],
        logId: data.log_id,
        time: getCurrentTime()
      });

      lastFailedQuery = null;

    } catch (err) {
      console.error('Chat error:', err);
      removeTypingIndicator(typingId);
      setLoadingState(false);

      // Render Error State with Retry Button
      appendErrorMessage(userText);
    }
  }

  function appendMessage(msg) {
    const row = document.createElement('div');
    row.className = `message-row message-${msg.sender}`;

    const avatarHtml = msg.sender === 'user' 
      ? `<div class="message-avatar avatar-user">You</div>`
      : `<div class="message-avatar avatar-bot">AI</div>`;

    let contentHtml = '';
    if (msg.sender === 'user') {
      contentHtml = `
        <div class="message-bubble bubble-user">
          ${escapeHtml(msg.text)}
          <div class="message-meta" style="color: rgba(255,255,255,0.85); justify-content: flex-end;">
            <span>${msg.time}</span>
          </div>
        </div>
      `;
    } else {
      // Format bot message text (handle line breaks and bold tags)
      const formattedText = formatBotText(msg.text);

      let statusBadge = '';
      if (msg.status === 'RESOLVED') {
        const confVal = parseFloat(msg.confidence) || 0;
        if (confVal >= 70) {
          statusBadge = `<span class="badge badge-resolved" style="background:#ecfdf5; color:#065f46; border:1px solid #a7f3d0;">✓ High Confidence (${msg.confidence}%)</span>`;
        } else {
          statusBadge = `<span class="badge badge-resolved">✓ Matched (${msg.confidence}%)</span>`;
        }
      } else if (msg.status === 'FALLBACK') {
        statusBadge = `<span class="badge badge-fallback">⚠ Department Referral</span>`;
      } else if (msg.status === 'GREETING') {
        statusBadge = `<span class="badge badge-primary">👋 Welcome</span>`;
      }

      let categoryBadge = '';
      if (msg.category) {
        categoryBadge = `<span class="badge cat-tag-${escapeHtml(msg.category)}">${escapeHtml(msg.category)}</span>`;
      }

      // Feedback Buttons
      let feedbackHtml = '';
      if (msg.logId) {
        feedbackHtml = `
          <div class="feedback-actions" data-log-id="${msg.logId}">
            <span style="font-size:0.75rem; color:var(--text-muted); margin-right:4px;">Helpful?</span>
            <button type="button" class="btn-feedback" data-log-id="${msg.logId}" data-value="HELPFUL" title="Helpful answer">
              👍 Yes
            </button>
            <button type="button" class="btn-feedback" data-log-id="${msg.logId}" data-value="NOT_HELPFUL" title="Not helpful">
              👎 No
            </button>
          </div>
        `;
      }

      // Copy Button
      const copyHtml = `
        <button type="button" class="btn-copy" data-answer="${escapeHtml(msg.text)}" title="Copy answer to clipboard">
          📋 Copy
        </button>
      `;

      // Suggested Related Questions Chips
      let suggestionsHtml = '';
      if (msg.suggestions && msg.suggestions.length > 0) {
        suggestionsHtml = `
          <div style="margin-top: 0.85rem; padding-top: 0.65rem; border-top: 1px dashed var(--border-subtle);">
            <div style="font-size: 0.78rem; font-weight: 600; color: var(--text-muted); margin-bottom: 0.35rem;">
              Suggested follow-up questions:
            </div>
            <div class="suggestion-chips">
              ${msg.suggestions.map(s => `
                <button type="button" class="chip" data-question="${escapeHtml(s.question)}">
                  💬 ${escapeHtml(s.question)}
                </button>
              `).join('')}
            </div>
          </div>
        `;
      }

      contentHtml = `
        <div class="message-bubble bubble-bot">
          <div style="margin-bottom: 0.6rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
            <div style="display: flex; align-items: center; gap: 0.4rem;">
              ${categoryBadge}
              ${statusBadge}
            </div>
            <div>
              ${copyHtml}
            </div>
          </div>
          <div class="bot-text">${formattedText}</div>
          ${suggestionsHtml}
          <div class="message-meta" style="justify-content: space-between; margin-top: 0.75rem;">
            <span>${msg.time}</span>
            ${feedbackHtml}
          </div>
        </div>
      `;
    }

    row.innerHTML = msg.sender === 'user' ? (contentHtml + avatarHtml) : (avatarHtml + contentHtml);
    chatMessages.appendChild(row);
    scrollToBottom();

    // Persist to sessionStorage
    saveChatToSession(msg);
  }

  function appendErrorMessage(failedQuery) {
    const row = document.createElement('div');
    row.className = 'message-row message-bot';
    row.innerHTML = `
      <div class="message-avatar avatar-bot" style="background: var(--danger-solid);">!</div>
      <div class="message-bubble bubble-bot" style="border-color: var(--danger-border); max-width: 480px;">
        <div class="chat-error-card">
          <div>
            <strong>Unable to connect to helpdesk server.</strong><br>
            <span style="font-size:0.8rem; opacity:0.85;">Please verify the application is running.</span>
          </div>
          <button type="button" class="btn btn-primary btn-sm btn-retry-query" style="background: var(--danger-solid); border:none;">
            ↻ Retry
          </button>
        </div>
      </div>
    `;
    chatMessages.appendChild(row);
    scrollToBottom();
  }

  function showTypingIndicator() {
    const id = 'typing-' + Date.now();
    const row = document.createElement('div');
    row.id = id;
    row.className = 'message-row message-bot';
    row.innerHTML = `
      <div class="message-avatar avatar-bot">AI</div>
      <div class="message-bubble bubble-bot" style="padding: 0.75rem 1rem;">
        <div class="typing-indicator-bubble">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <span style="font-size: 0.8rem; color: var(--text-muted); margin-left: 6px;">Campus Assistant is thinking...</span>
        </div>
      </div>
    `;
    chatMessages.appendChild(row);
    scrollToBottom();
    return id;
  }

  function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function setLoadingState(isLoading) {
    if (chatInput) chatInput.disabled = isLoading;
    if (chatSendBtn) {
      chatSendBtn.disabled = isLoading;
      if (isLoading) {
        if (chatSendText) chatSendText.textContent = '';
        if (chatSendIcon) chatSendIcon.innerHTML = `<span class="btn-spinner"></span>`;
      } else {
        if (chatSendText) chatSendText.textContent = 'Send';
        if (chatSendIcon) {
          chatSendIcon.innerHTML = `
            <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path>
            </svg>
          `;
        }
        if (chatInput) chatInput.focus();
      }
    }
  }

  async function submitFeedback(logId, val, container) {
    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ log_id: logId, feedback: val })
      });
      const data = await res.json();
      if (data.success) {
        container.innerHTML = `
          <span style="font-size:0.75rem; color:var(--success-solid); font-weight:600;">
            ✓ Thank you for your feedback!
          </span>
        `;
      }
    } catch (e) {
      console.error('Feedback submit error:', e);
    }
  }

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatBotText(text) {
    if (!text) return '';
    let escaped = escapeHtml(text);
    // Convert markdown bold **bold** to <strong>bold</strong>
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Convert bullet points
    escaped = escaped.replace(/\n• (.*?)/g, '<br>• $1');
    // Convert remaining newlines
    escaped = escaped.replace(/\n/g, '<br>');
    return escaped;
  }

  function saveChatToSession(msg) {
    try {
      const history = JSON.parse(sessionStorage.getItem('sfaq_chat_history') || '[]');
      history.push(msg);
      if (history.length > 30) history.shift();
      sessionStorage.setItem('sfaq_chat_history', JSON.stringify(history));
    } catch (e) {}
  }

  function restoreChatSession() {
    try {
      const saved = sessionStorage.getItem('sfaq_chat_history');
      if (saved) {
        const history = JSON.parse(saved);
        if (history.length > 0) {
          chatMessages.innerHTML = '';
          history.forEach(msg => appendMessage(msg));
          return;
        }
      }
    } catch (e) {}
    renderEmptyState();
  }

  function renderEmptyState() {
    if (chatMessages.children.length === 0) {
      const emptyDiv = document.createElement('div');
      emptyDiv.id = 'chat-empty-state';
      emptyDiv.className = 'chat-empty-state';
      emptyDiv.innerHTML = `
        <div class="chat-empty-avatar">🎓</div>
        <h3 class="chat-empty-title">Welcome to Campus Helpdesk</h3>
        <p class="chat-empty-desc">
          I am your AI-powered college assistant. Ask any question in natural language or choose a popular inquiry below:
        </p>
        <div class="chat-welcome-prompts">
          <button type="button" class="welcome-prompt-btn" data-question="What is the minimum attendance requirement to appear for semester exams?">
            <span class="welcome-prompt-cat">📖 Academics</span>
            <span>What is the 75% attendance rule?</span>
          </button>
          <button type="button" class="welcome-prompt-btn" data-question="What are the accepted payment modes for college semester tuition fees?">
            <span class="welcome-prompt-cat">💳 Fees</span>
            <span>How can I pay semester fees online?</span>
          </button>
          <button type="button" class="welcome-prompt-btn" data-question="How and when can I download my examination hall ticket?">
            <span class="welcome-prompt-cat">📝 Examinations</span>
            <span>How to download exam hall ticket?</span>
          </button>
          <button type="button" class="welcome-prompt-btn" data-question="What are the central library working hours and timings?">
            <span class="welcome-prompt-cat">📚 Library</span>
            <span>Central Library working hours?</span>
          </button>
        </div>
      `;
      chatMessages.appendChild(emptyDiv);
    }
  }

  // Mobile Sidebar Drawer Handlers
  function initChatSidebarDrawer() {
    if (!chatSidebarToggle || !chatSidebar || !chatSidebarBackdrop) return;

    chatSidebarToggle.addEventListener('click', () => {
      chatSidebar.classList.add('drawer-open');
      chatSidebarBackdrop.classList.add('drawer-open');
    });

    if (chatSidebarClose) {
      chatSidebarClose.addEventListener('click', closeChatSidebarDrawer);
    }

    chatSidebarBackdrop.addEventListener('click', closeChatSidebarDrawer);
  }

  function closeChatSidebarDrawer() {
    if (chatSidebar) chatSidebar.classList.remove('drawer-open');
    if (chatSidebarBackdrop) chatSidebarBackdrop.classList.remove('drawer-open');
  }
});
