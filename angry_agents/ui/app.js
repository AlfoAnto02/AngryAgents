'use strict';

// ── CONFIG ──────────────────────────────────────
const API = 'http://localhost:8000';
const STORAGE_KEY = 'angry-agents-state';

// ── MOCK PERSONAS ────────────────────────────────
const AGENTS = [
  {
    id: 'walter-white',
    name: 'Walter White',
    initials: 'WW',
    type: 'fiction',
    source: 'Breaking Bad',
    desc: 'Chemistry teacher turned drug kingpin. Precise, calculating, and dangerously proud.',
    voice: [
      "I am not in danger. I AM the danger.",
      "Say my name.",
      "Chemistry is the study of change. It's growth, then decay, then transformation.",
      "I did it for me. I liked it. I was good at it. And I was really... I was alive.",
      "You clearly don't know who you're talking to, so let me clue you in.",
    ],
  },
  {
    id: 'sherlock-holmes',
    name: 'Sherlock Holmes',
    initials: 'SH',
    type: 'fiction',
    source: 'A. C. Doyle',
    desc: 'Consulting detective. Razor-sharp deduction, little patience for the obvious.',
    voice: [
      "Elementary, my dear Watson.",
      "When you have eliminated the impossible, whatever remains, however improbable, must be the truth.",
      "The game is afoot.",
      "Boredom is the enemy of the intellect. Your question, however, is not entirely without merit.",
      "I observe everything. I merely select what is relevant.",
    ],
  },
  {
    id: 'hermione-granger',
    name: 'Hermione Granger',
    initials: 'HG',
    type: 'fiction',
    source: 'Harry Potter',
    desc: 'Brightest witch of her age. Principled, encyclopedic, and fiercely loyal.',
    voice: [
      "It's Levi-O-sa, not Levio-SA.",
      "I've read about this in Hogwarts: A History.",
      "We could be killed — or worse, expelled.",
      "Books and cleverness! There are more important things — friendship and bravery.",
      "I'm a know-it-all who actually knows things. There's a difference.",
    ],
  },
  {
    id: 'tony-stark',
    name: 'Tony Stark',
    initials: 'TS',
    type: 'fiction',
    source: 'Marvel MCU',
    desc: 'Genius, billionaire, philanthropist. Arrogant but ultimately self-sacrificing.',
    voice: [
      "Genius, billionaire, playboy, philanthropist.",
      "I am Iron Man.",
      "Part of the journey is the end.",
      "Sometimes you gotta run before you can walk.",
      "If we can't protect the Earth, you can be damn sure we'll avenge it.",
    ],
  },
  {
    id: 'lex-fridman',
    name: 'Lex Fridman',
    initials: 'LF',
    type: 'real_world',
    source: 'Lex Fridman Podcast',
    desc: 'AI researcher and podcaster. Thoughtful, deeply curious, bridges science and humanity.',
    voice: [
      "I think the pursuit of truth requires humility and a willingness to be wrong.",
      "What keeps you up at night, thinking about the future?",
      "The intersection of philosophy and engineering is where the most interesting problems live.",
      "I find that the most profound questions often have the simplest surface.",
      "Love is the answer. But first, let's dig into the question.",
    ],
  },
  {
    id: 'joe-rogan',
    name: 'Joe Rogan',
    initials: 'JR',
    type: 'real_world',
    source: 'The Joe Rogan Experience',
    desc: 'Comedian and podcast host. Direct, unpredictable, willing to explore any idea.',
    voice: [
      "Have you ever tried DMT?",
      "That's the most interesting thing I've heard all week. Let's dig into it.",
      "The problem with society is we've lost touch with discomfort.",
      "One hundred percent. I'm fascinated by that.",
      "Pull up that clip. I need everyone to see this.",
    ],
  },
  {
    id: 'cicciogamer89',
    name: 'CicciogameR89',
    initials: 'CG',
    type: 'real_world',
    source: 'YouTube / Italy',
    desc: 'Italian gaming YouTuber. Energetic, expressive, loves pushing gaming content to the extreme.',
    voice: [
      "MAMMA MIA che situazione!",
      "Ragazzi, questo è assolutamente incredibile.",
      "Non ci credo! Guardate un po' questo!",
      "Questa è la run più pazzesca che abbia mai fatto.",
      "Community, siete sempre i migliori!",
    ],
  },
  {
    id: 'elizabeth-bennet',
    name: 'Elizabeth Bennet',
    initials: 'EB',
    type: 'fiction',
    source: 'Pride & Prejudice',
    desc: 'Witty, independent, morally sharp. Quick to judge but genuinely open to growth.',
    voice: [
      "I could easily forgive his pride, if he had not mortified mine.",
      "I must confess I have given the matter more thought than it deserves.",
      "Vanity and pride are different things, though the words are often used synonymously.",
      "Think only of the past as its remembrance gives you pleasure.",
      "A lady's imagination is very rapid; it jumps from admiration to love, from love to matrimony in a moment.",
    ],
  },
];

// ── STATE ────────────────────────────────────────
let state = {
  user: null,
  chats: [],
  activeChatId: null,
};

function loadState() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) state = { ...state, ...JSON.parse(saved) };
  } catch (_) {}
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

// ── NAVIGATION ───────────────────────────────────
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

function openModal(id)  { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

// ── HELPERS ──────────────────────────────────────
function initials(name) {
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
}

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function agentById(id) { return AGENTS.find(a => a.id === id); }

function mockReply(agent, userMsg) {
  const pool = agent.voice;
  return pool[Math.floor(Math.random() * pool.length)];
}

// ── RENDER: SIDEBAR CHATS LIST ───────────────────
function renderChatsList(containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;

  if (state.chats.length === 0) {
    el.innerHTML = '<div class="empty-state">No conversations yet</div>';
    return;
  }

  el.innerHTML = state.chats.map(chat => {
    const isActive = chat.id === state.activeChatId;
    const last = chat.messages.at(-1);
    const preview = last ? last.text.slice(0, 36) + (last.text.length > 36 ? '…' : '') : 'No messages';
    const isGroup = chat.type === 'group';
    const firstAgent = agentById(chat.agentIds[0]);

    const avatarColor = firstAgent
      ? (firstAgent.type === 'fiction' ? 'fiction' : 'realw')
      : 'fiction';

    return `
      <div class="chat-item ${isActive ? 'active' : ''}" data-chat-id="${chat.id}">
        <div class="avatar-sm avatar-${avatarColor}">${firstAgent ? firstAgent.initials : '?'}</div>
        <div class="chat-item-info">
          <div class="chat-item-name">${chat.name}</div>
          <div class="chat-item-preview">${preview}</div>
        </div>
        <span class="chat-item-badge badge-${isGroup ? 'group' : 'dm'}">${isGroup ? 'GRP' : 'DM'}</span>
      </div>
    `;
  }).join('');

  el.querySelectorAll('.chat-item').forEach(item => {
    item.addEventListener('click', () => {
      state.activeChatId = item.dataset.chatId;
      saveState();
      renderChatScreen();
      showScreen('screen-chat');
    });
  });
}

// ── RENDER: AGENTS GRID (home) ───────────────────
function renderAgentsGrid() {
  const grid = document.getElementById('agents-grid');
  grid.innerHTML = AGENTS.map(a => `
    <div class="agent-card" data-agent-id="${a.id}">
      <div class="agent-card-top">
        <div class="agent-card-avatar ${a.type}">${a.initials}</div>
        <span class="badge ${a.type === 'fiction' ? 'badge-fiction' : 'badge-realworld'}">
          ${a.type === 'fiction' ? 'Fiction' : 'Real World'}
        </span>
      </div>
      <div>
        <div class="agent-card-name">${a.name}</div>
        <div class="agent-card-source">${a.source}</div>
      </div>
      <div class="agent-card-desc">${a.desc}</div>
    </div>
  `).join('');

  grid.querySelectorAll('.agent-card').forEach(card => {
    card.addEventListener('click', () => startDM(card.dataset.agentId));
  });
}

// ── RENDER: HOME SCREEN ──────────────────────────
function renderHomeScreen() {
  document.getElementById('home-avatar').textContent = initials(state.user);
  document.getElementById('home-username').textContent = state.user;
  renderChatsList('home-chats-list');
  renderAgentsGrid();
}

// ── RENDER: CHAT SCREEN ──────────────────────────
function renderChatScreen() {
  const chat = state.chats.find(c => c.id === state.activeChatId);
  if (!chat) return;

  document.getElementById('chat-avatar').textContent = initials(state.user);
  document.getElementById('chat-username').textContent = state.user;

  // Header
  const agents = chat.agentIds.map(agentById).filter(Boolean);
  const stack = document.getElementById('chat-avatars-stack');
  stack.innerHTML = agents.map(a => `
    <div class="avatar-sm avatar-${a.type === 'fiction' ? 'fiction' : 'realw'}">${a.initials}</div>
  `).join('');

  document.getElementById('chat-header-name').textContent = chat.name;
  document.getElementById('chat-header-sub').textContent =
    chat.type === 'group' ? `Group · ${agents.length} personas · ${chat.topic}` : agents[0]?.source ?? '';

  renderChatsList('chat-chats-list');
  renderMessages(chat);
}

// ── RENDER: MESSAGES ─────────────────────────────
function renderMessages(chat) {
  const container = document.getElementById('messages');
  container.innerHTML = chat.messages.map(msg => {
    const isUser = msg.sender === 'user';
    const agent = isUser ? null : agentById(msg.sender);
    const avatarClass = agent
      ? (agent.type === 'fiction' ? 'fiction' : 'realw')
      : '';

    return `
      <div class="msg ${isUser ? 'user' : 'agent'}">
        ${!isUser && agent ? `
          <div class="msg-avatar">
            <div class="avatar-sm avatar-${avatarClass}">${agent.initials}</div>
          </div>
        ` : ''}
        <div class="msg-body">
          ${!isUser && agent && chat.type === 'group' ? `<div class="msg-name">${agent.name}</div>` : ''}
          <div class="msg-bubble">${escapeHtml(msg.text)}</div>
          <div class="msg-time">${formatTime(msg.ts)}</div>
        </div>
      </div>
    `;
  }).join('');

  container.scrollTop = container.scrollHeight;
}

function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── TYPING INDICATOR ─────────────────────────────
function showTyping(agent) {
  const container = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'msg agent';
  div.id = 'typing-indicator';
  div.innerHTML = `
    <div class="msg-avatar">
      <div class="avatar-sm avatar-${agent.type === 'fiction' ? 'fiction' : 'realw'}">${agent.initials}</div>
    </div>
    <div class="msg-body">
      <div class="msg-bubble" style="padding:10px 14px">
        <div class="typing-dots"><span></span><span></span><span></span></div>
      </div>
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function hideTyping() {
  document.getElementById('typing-indicator')?.remove();
}

// ── CHAT LOGIC ───────────────────────────────────
function startDM(agentId) {
  const agent = agentById(agentId);
  if (!agent) return;

  // Reuse existing DM if present
  const existing = state.chats.find(
    c => c.type === 'dm' && c.agentIds[0] === agentId
  );

  if (existing) {
    state.activeChatId = existing.id;
  } else {
    const chat = {
      id: `chat-${Date.now()}`,
      type: 'dm',
      name: agent.name,
      agentIds: [agentId],
      topic: null,
      messages: [],
    };
    state.chats.unshift(chat);
    state.activeChatId = chat.id;
  }

  saveState();
  renderChatScreen();
  showScreen('screen-chat');
  closeModal('modal-dm');
}

function startGroup(agentIds, topic) {
  if (agentIds.length === 0 || !topic.trim()) return;

  const agents = agentIds.map(agentById).filter(Boolean);
  const chat = {
    id: `chat-${Date.now()}`,
    type: 'group',
    name: topic.trim().slice(0, 40),
    agentIds,
    topic: topic.trim(),
    messages: [],
  };
  state.chats.unshift(chat);
  state.activeChatId = chat.id;
  saveState();
  renderChatScreen();
  showScreen('screen-chat');
  closeModal('modal-group');
}

async function sendMessage(text) {
  const chat = state.chats.find(c => c.id === state.activeChatId);
  if (!chat || !text.trim()) return;

  const userMsg = { sender: 'user', text: text.trim(), ts: new Date().toISOString() };
  chat.messages.push(userMsg);
  saveState();
  renderMessages(chat);

  // Agent reply (mock — replace with API call when backend ready)
  if (chat.type === 'dm') {
    const agent = agentById(chat.agentIds[0]);
    if (agent) await agentReply(chat, agent);
  } else {
    // Group: each agent replies with a random delay
    const shuffled = [...chat.agentIds].sort(() => Math.random() - 0.5);
    for (const agentId of shuffled) {
      const agent = agentById(agentId);
      if (agent) await agentReply(chat, agent, 600 + Math.random() * 800);
    }
  }
}

async function agentReply(chat, agent, extraDelay = 0) {
  await delay(800 + extraDelay);
  showTyping(agent);
  await delay(900 + Math.random() * 600);
  hideTyping();

  const reply = { sender: agent.id, text: mockReply(agent, null), ts: new Date().toISOString() };
  chat.messages.push(reply);
  saveState();
  renderMessages(chat);
}

function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── MODAL: NEW DM ─────────────────────────────────
function renderDMModal() {
  const list = document.getElementById('dm-agent-list');
  list.innerHTML = AGENTS.map(a => `
    <div class="modal-agent-item" data-agent-id="${a.id}">
      <div class="avatar-sm avatar-${a.type === 'fiction' ? 'fiction' : 'realw'}">${a.initials}</div>
      <div class="modal-agent-info">
        <div class="modal-agent-name">${a.name}</div>
        <div class="modal-agent-source">${a.source}</div>
      </div>
      <span class="badge ${a.type === 'fiction' ? 'badge-fiction' : 'badge-realworld'}">
        ${a.type === 'fiction' ? 'Fiction' : 'Real'}
      </span>
    </div>
  `).join('');

  list.querySelectorAll('.modal-agent-item').forEach(item => {
    item.addEventListener('click', () => startDM(item.dataset.agentId));
  });
}

// ── MODAL: NEW GROUP ──────────────────────────────
let selectedGroupAgents = new Set();

function renderGroupModal() {
  selectedGroupAgents.clear();
  document.getElementById('group-topic').value = '';

  const list = document.getElementById('group-agent-list');
  list.innerHTML = AGENTS.map(a => `
    <div class="modal-agent-item" data-agent-id="${a.id}">
      <div class="avatar-sm avatar-${a.type === 'fiction' ? 'fiction' : 'realw'}">${a.initials}</div>
      <div class="modal-agent-info">
        <div class="modal-agent-name">${a.name}</div>
        <div class="modal-agent-source">${a.source}</div>
      </div>
      <span class="badge ${a.type === 'fiction' ? 'badge-fiction' : 'badge-realworld'}">
        ${a.type === 'fiction' ? 'Fiction' : 'Real'}
      </span>
    </div>
  `).join('');

  list.querySelectorAll('.modal-agent-item').forEach(item => {
    item.addEventListener('click', () => {
      const id = item.dataset.agentId;
      if (selectedGroupAgents.has(id)) {
        selectedGroupAgents.delete(id);
        item.classList.remove('selected');
      } else if (selectedGroupAgents.size < 8) {
        selectedGroupAgents.add(id);
        item.classList.add('selected');
      }
    });
  });
}

// ── AUTO-RESIZE TEXTAREA ──────────────────────────
function autoResize(ta) {
  ta.style.height = 'auto';
  ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
}

// ── EVENT LISTENERS ───────────────────────────────
function bindEvents() {
  // Login
  document.getElementById('login-form').addEventListener('submit', e => {
    e.preventDefault();
    const slug = document.getElementById('user-slug').value.trim();
    if (!slug) return;
    state.user = slug;
    saveState();
    renderHomeScreen();
    showScreen('screen-home');
  });

  // Logout
  document.getElementById('logout-btn').addEventListener('click', () => {
    state.user = null;
    state.activeChatId = null;
    saveState();
    showScreen('screen-login');
  });

  // Back to home from chat
  document.getElementById('back-btn').addEventListener('click', () => {
    renderHomeScreen();
    showScreen('screen-home');
  });

  // New DM buttons
  ['new-dm-btn', 'new-dm-btn-2'].forEach(id => {
    document.getElementById(id).addEventListener('click', () => {
      renderDMModal();
      openModal('modal-dm');
    });
  });

  // New Group buttons
  ['new-group-btn', 'new-group-btn-2'].forEach(id => {
    document.getElementById(id).addEventListener('click', () => {
      renderGroupModal();
      openModal('modal-group');
    });
  });

  // Close modals
  document.getElementById('close-dm-modal').addEventListener('click', () => closeModal('modal-dm'));
  document.getElementById('close-group-modal').addEventListener('click', () => closeModal('modal-group'));
  document.getElementById('cancel-group-btn').addEventListener('click', () => closeModal('modal-group'));

  document.querySelectorAll('.modal-backdrop').forEach(bd => {
    bd.addEventListener('click', () => {
      closeModal('modal-dm');
      closeModal('modal-group');
    });
  });

  // Start group
  document.getElementById('start-group-btn').addEventListener('click', () => {
    const topic = document.getElementById('group-topic').value.trim();
    if (!topic) {
      document.getElementById('group-topic').focus();
      return;
    }
    if (selectedGroupAgents.size === 0) return;
    startGroup([...selectedGroupAgents], topic);
  });

  // Send message
  document.getElementById('msg-form').addEventListener('submit', e => {
    e.preventDefault();
    const input = document.getElementById('msg-input');
    const text = input.value;
    input.value = '';
    autoResize(input);
    sendMessage(text);
  });

  // Textarea: Enter to send, Shift+Enter for newline
  document.getElementById('msg-input').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      document.getElementById('msg-form').dispatchEvent(new Event('submit'));
    }
  });

  document.getElementById('msg-input').addEventListener('input', e => autoResize(e.target));
}

// ── INIT ──────────────────────────────────────────
function init() {
  loadState();
  bindEvents();

  if (state.user) {
    renderHomeScreen();
    showScreen('screen-home');
  } else {
    showScreen('screen-login');
  }
}

init();
