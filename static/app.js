document.addEventListener('DOMContentLoaded', () => {
  const messagesContainer = document.getElementById('messages-container');
  const chatForm = document.getElementById('chat-form');
  const chatInput = document.getElementById('chat-input');
  const userIdInput = document.getElementById('user-id-input');
  const evalToggle = document.getElementById('eval-toggle');
  const fileInput = document.getElementById('file-input');
  const dropzone = document.getElementById('upload-dropzone');
  const memoriesList = document.getElementById('memories-list');
  const modelTag = document.getElementById('model-tag');
  const langsmithTag = document.getElementById('langsmith-tag');

  // Image Attachment Elements
  const attachImageBtn = document.getElementById('attach-image-btn');
  const chatImageInput = document.getElementById('chat-image-input');
  const imagePreviewContainer = document.getElementById('image-preview-container');
  const attachedImageName = document.getElementById('attached-image-name');
  const removeImageBtn = document.getElementById('remove-image-btn');

  let currentChatId = null;
  let attachedImageData = null;

  // Image attachment handler
  if (attachImageBtn && chatImageInput) {
    attachImageBtn.addEventListener('click', () => chatImageInput.click());
    chatImageInput.addEventListener('change', () => {
      const file = chatImageInput.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
          attachedImageData = e.target.result;
          attachedImageName.textContent = file.name;
          imagePreviewContainer.style.display = 'flex';
        };
        reader.readAsDataURL(file);
      }
    });
  }

  if (removeImageBtn) {
    removeImageBtn.addEventListener('click', () => {
      attachedImageData = null;
      chatImageInput.value = '';
      imagePreviewContainer.style.display = 'none';
    });
  }

  // 1. Check System Health & Config
  async function checkHealth() {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        const data = await res.json();
        modelTag.textContent = data.model || 'Groq Active';
        if (data.langsmith_enabled) {
          langsmithTag.textContent = `LangSmith: ${data.langsmith_project}`;
          langsmithTag.style.color = '#34d399';
        } else {
          langsmithTag.textContent = 'LangSmith: Off';
          langsmithTag.style.color = '#9ca3af';
        }
      }
    } catch (err) {
      console.warn('Health check failed:', err);
    }
  }

  // 2. Fetch User Memories
  async function loadMemories() {
    const userId = userIdInput.value.trim();
    if (!userId) return;

    try {
      const res = await fetch(`/api/memories/${encodeURIComponent(userId)}`);
      if (res.ok) {
        const memories = await res.json();
        memoriesList.innerHTML = '';
        if (memories.length === 0) {
          memoriesList.innerHTML = '<div class="memory-item">No durable facts recorded yet.</div>';
        } else {
          memories.forEach(fact => {
            const item = document.createElement('div');
            item.className = 'memory-item';
            item.textContent = `• ${fact}`;
            memoriesList.appendChild(item);
          });
        }
      }
    } catch (err) {
      console.warn('Load memories failed:', err);
    }
  }

  userIdInput.addEventListener('change', loadMemories);

  // 3. Handle Chat Submission
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const prompt = chatInput.value.trim();
    if (!prompt && !attachedImageData) return;

    const userId = userIdInput.value.trim() || null;
    const runEval = evalToggle.checked;
    const imagePayload = attachedImageData;

    // Reset attached image state
    const currentPrompt = prompt || "Analyze the attached image in detail.";
    attachedImageData = null;
    if (chatImageInput) chatImageInput.value = '';
    if (imagePreviewContainer) imagePreviewContainer.style.display = 'none';

    // Append User Message (with image preview if present)
    appendMessage('user', currentPrompt, null, null, null, imagePayload);
    chatInput.value = '';

    // Append Typing Indicator
    const typingElem = appendTypingIndicator();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_inp: currentPrompt,
          user_id: userId,
          chat_id: currentChatId,
          image_data: imagePayload,
          eval_response: runEval
        })
      });

      typingElem.remove();

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const data = await response.json();
      currentChatId = data.chat_id;

      // Append Assistant Message
      appendMessage('assistant', data.output, data.route, data.context, data.eval_scores);

      // Refresh memories after run
      setTimeout(loadMemories, 1500);

    } catch (err) {
      typingElem.remove();
      appendMessage('assistant', `⚠️ Request failed: ${err.message}`, 'error');
    }
  });

  // Helper: Append Message Bubble
  function appendMessage(role, text, route = null, context = null, evalScores = null, imageSrc = null) {
    const bubble = document.createElement('div');
    bubble.className = `message-bubble ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = role === 'user' ? 'U' : 'M';

    const box = document.createElement('div');
    box.className = 'content-box';

    if (role === 'assistant' && route) {
      const badge = document.createElement('span');
      badge.className = `route-badge ${route}`;
      badge.textContent = `Route: ${route}`;
      box.appendChild(badge);
    }

    if (imageSrc) {
      const img = document.createElement('img');
      img.src = imageSrc;
      img.style.maxWidth = '260px';
      img.style.maxHeight = '200px';
      img.style.borderRadius = '8px';
      img.style.marginBottom = '8px';
      img.style.display = 'block';
      box.appendChild(img);
    }

    const textElem = document.createElement('div');
    textElem.className = 'message-text';
    textElem.textContent = text;
    box.appendChild(textElem);

    // Show Context Accordion if available
    if (context && context !== '(no relevant context found)') {
      const accordion = document.createElement('div');
      accordion.className = 'context-accordion';

      const toggleBtn = document.createElement('button');
      toggleBtn.className = 'context-toggle';
      toggleBtn.innerHTML = '🔍 View RAG Context ▼';

      const body = document.createElement('div');
      body.className = 'context-body';
      body.textContent = context;

      toggleBtn.addEventListener('click', () => {
        body.classList.toggle('open');
        toggleBtn.innerHTML = body.classList.contains('open') ? '🔍 Hide RAG Context ▲' : '🔍 View RAG Context ▼';
      });

      accordion.appendChild(toggleBtn);
      accordion.appendChild(body);
      box.appendChild(accordion);
    }

    bubble.appendChild(avatar);
    bubble.appendChild(box);
    messagesContainer.appendChild(bubble);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  // Helper: Typing Indicator
  function appendTypingIndicator() {
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble assistant';
    bubble.innerHTML = `
      <div class="avatar">M</div>
      <div class="content-box">
        <div class="typing-indicator">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    `;
    messagesContainer.appendChild(bubble);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    return bubble;
  }

  // 4. Handle File Ingestion
  dropzone.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', async () => {
    if (!fileInput.files.length) return;
    const file = fileInput.files[0];
    const userId = userIdInput.value.trim();

    const formData = new FormData();
    formData.append('file', file);

    dropzone.querySelector('.dropzone-text').textContent = `Uploading ${file.name}...`;

    try {
      const url = userId ? `/api/ingest?user_id=${encodeURIComponent(userId)}` : '/api/ingest';
      const res = await fetch(url, { method: 'POST', body: formData });
      if (res.ok) {
        const data = await res.json();
        dropzone.querySelector('.dropzone-text').textContent = `✅ Ingested ${data.chunks_added} chunks!`;
        appendMessage('assistant', `📄 Ingested document '${file.name}' into RAG store (${data.chunks_added} text chunks indexed).`, 'rag_agent');
      } else {
        dropzone.querySelector('.dropzone-text').textContent = `❌ Ingestion failed.`;
      }
    } catch (err) {
      dropzone.querySelector('.dropzone-text').textContent = `❌ Ingestion error.`;
    }
  });

  // Initial Boot
  checkHealth();
  loadMemories();
});
