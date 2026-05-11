'use strict';

const API_BASE = 'http://localhost:8000';
const STORAGE_KEY = 'angry-agents-v1';

// ── MOCK PERSONAS ────────────────────────────────────────────────────────────
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
      "Chemistry is the study of change. Growth, then decay, then transformation.",
      "I did it for me. I liked it. I was good at it. And I was really — I was alive.",
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
      "Elementary.",
      "When you eliminate the impossible, whatever remains — however improbable — must be the truth.",
      "The game is afoot.",
      "Boredom is the enemy of the intellect. Your question, however, is not entirely without merit.",
      "Data, data, data. I cannot make bricks without clay.",
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
      "I've read about this — extensively.",
      "We could be killed — or worse, expelled.",
      "Books and cleverness! There are more important things — friendship and bravery.",
      "Now if you two don't mind, I'm going to bed before either of you comes up with another clever idea to get us killed.",
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
    desc: 'AI researcher and podcaster. Deeply curious, bridges science and humanity.',
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
      "One hundred percent. I'm genuinely fascinated by that.",
      "Pull up that clip. I need everyone to see this.",
    ],
  },
  {
    id: 'cicciogamer89',
    name: 'CicciogameR89',
    initials: 'CG',
    type: 'real_world',
    source: 'YouTube / Italy',
    desc: 'Italian gaming YouTuber. Energetic, expressive, passionate about gaming.',
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
    desc: 'Witty, independent, morally sharp. Quick to judge but open to growth.',
    voice: [
      "I could easily forgive his pride, if he had not mortified mine.",
      "I must confess I have given the matter more thought than it deserves.",
      "Vanity and pride are different things, though the words are often used synonymously.",
      "Think only of the past as its remembrance gives you pleasure.",
      "A lady's imagination is very rapid; it jumps from admiration to love, from love to matrimony in a moment.",
    ],
  },
];

// ── STATE ────────────────────────────────────────────────────────────────────
let state = { user: null, chats: [], activeChatId: null };

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) state = { ...state, ...JSON.parse(raw) };
  } catch (_) {}
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

// ── NAV ──────────────────────────────────────────────────────────────────────
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

function openModal(id)  { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

// ── HELPERS ──────────────────────────────────────────────────────────────────
const initials = name => name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
const formatTime = iso => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
const agentById = id => AGENTS.find(a => a.id === id);
const escHtml = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const delay = ms => new Promise(r => setTimeout(r, ms));

function mockReply(agent) {
  return agent.voice[Math.floor(Math.random() * agent.voice.length)];
}

// ── RENDER: CHATS SIDEBAR ────────────────────────────────────────────────────
function renderChatsList(containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;

  if (!state.chats.length) {
    el.innerHTML = '<div class="empty-state">No conversations yet</div>';
    return;
  }

  el.innerHTML = state.chats.map(chat => {
    const active = chat.id === state.activeChatId;
    const last = chat.messages.at(-1);
    const preview = last ? last.text.slice(0, 38) + (last.text.length > 38 ? '…' : '') : 'No messages';
    const agent = agentById(chat.agentIds[0]);
    const avClass = agent ? (agent.type === 'fiction' ? 'fiction' : 'realw') : 'fiction';
    const isGroup = chat.type === 'group';

    return `
      <div class="chat-item${active ? ' active' : ''}" data-id="${chat.id}">
        <div class="avatar-sm avatar-${avClass}">${agent ? agent.initials : '?'}</div>
        <div class="chat-item-info">
          <div class="chat-item-name">${escHtml(chat.name)}</div>
          <div class="chat-item-preview">${escHtml(preview)}</div>
        </div>
        <span class="chat-item-badge badge-${isGroup ? 'group' : 'dm'}">${isGroup ? 'GRP' : 'DM'}</span>
      </div>`;
  }).join('');

  el.querySelectorAll('.chat-item').forEach(item => {
    item.addEventListener('click', () => {
      state.activeChatId = item.dataset.id;
      saveState();
      renderChatScreen();
      showScreen('screen-chat');
    });
  });
}

// ── RENDER: AGENTS GRID ──────────────────────────────────────────────────────
function renderAgentsGrid() {
  document.getElementById('agents-grid').innerHTML = AGENTS.map(a => `
    <div class="agent-card" data-id="${a.id}">
      <div class="agent-card-top">
        <div class="agent-card-avatar ${a.type}">${a.initials}</div>
        <span class="badge ${a.type === 'fiction' ? 'badge-fiction' : 'badge-realworld'}">
          ${a.type === 'fiction' ? 'Fiction' : 'Real World'}
        </span>
      </div>
      <div>
        <div class="agent-card-name">${escHtml(a.name)}</div>
        <div class="agent-card-source">${escHtml(a.source)}</div>
      </div>
      <div class="agent-card-desc">${escHtml(a.desc)}</div>
    </div>
  `).join('');

  document.getElementById('agents-grid').querySelectorAll('.agent-card').forEach(card => {
    card.addEventListener('click', () => startDM(card.dataset.id));
  });
}

// ── RENDER: HOME ─────────────────────────────────────────────────────────────
function renderHomeScreen() {
  const av = document.getElementById('home-avatar');
  av.textContent = initials(state.user);
  document.getElementById('home-username').textContent = state.user;
  renderChatsList('home-chats-list');
  renderAgentsGrid();
}

// ── RENDER: CHAT ─────────────────────────────────────────────────────────────
function renderChatScreen() {
  const chat = state.chats.find(c => c.id === state.activeChatId);
  if (!chat) return;

  document.getElementById('chat-avatar').textContent = initials(state.user);
  document.getElementById('chat-username').textContent = state.user;

  const agents = chat.agentIds.map(agentById).filter(Boolean);

  document.getElementById('chat-avatars-stack').innerHTML = agents.map(a => `
    <div class="avatar-sm avatar-${a.type === 'fiction' ? 'fiction' : 'realw'}">${a.initials}</div>
  `).join('');

  document.getElementById('chat-header-name').textContent = chat.name;
  document.getElementById('chat-header-sub').textContent = chat.type === 'group'
    ? `Group · ${agents.length} personas · ${chat.topic}`
    : agents[0]?.source ?? '';

  renderChatsList('chat-chats-list');
  renderMessages(chat);
}

// ── RENDER: MESSAGES ─────────────────────────────────────────────────────────
function renderMessages(chat) {
  const box = document.getElementById('messages');

  box.innerHTML = chat.messages.map(msg => {
    const isUser = msg.sender === 'user';
    const agent = isUser ? null : agentById(msg.sender);
    const avClass = agent ? (agent.type === 'fiction' ? 'fiction' : 'realw') : '';

    return `
      <div class="msg ${isUser ? 'user' : 'agent'}">
        ${!isUser && agent ? `
          <div class="msg-avatar">
            <div class="avatar-sm avatar-${avClass}">${agent.initials}</div>
          </div>` : ''}
        <div class="msg-body">
          ${!isUser && agent && chat.type === 'group'
            ? `<div class="msg-name">${escHtml(agent.name)}</div>` : ''}
          <div class="msg-bubble">${escHtml(msg.text)}</div>
          <div class="msg-time">${formatTime(msg.ts)}</div>
        </div>
      </div>`;
  }).join('');

  box.scrollTop = box.scrollHeight;
}

// ── TYPING INDICATOR ─────────────────────────────────────────────────────────
function showTyping(agent) {
  const box = document.getElementById('messages');
  const div = document.createElement('div');
  div.id = 'typing-indicator';
  div.className = 'msg agent';
  div.innerHTML = `
    <div class="msg-avatar">
      <div class="avatar-sm avatar-${agent.type === 'fiction' ? 'fiction' : 'realw'}">${agent.initials}</div>
    </div>
    <div class="msg-body">
      <div class="msg-bubble" style="padding:10px 14px">
        <div class="typing-dots"><span></span><span></span><span></span></div>
      </div>
    </div>`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function hideTyping() {
  document.getElementById('typing-indicator')?.remove();
}

// ── CHAT LOGIC ───────────────────────────────────────────────────────────────
function startDM(agentId) {
  const agent = agentById(agentId);
  if (!agent) return;

  const existing = state.chats.find(c => c.type === 'dm' && c.agentIds[0] === agentId);
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
  if (!agentIds.length || !topic.trim()) return;

  const chat = {
    id: `chat-${Date.now()}`,
    type: 'group',
    name: topic.trim().slice(0, 42),
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

  chat.messages.push({ sender: 'user', text: text.trim(), ts: new Date().toISOString() });
  saveState();
  renderMessages(chat);

  // TODO: replace mock replies with real API calls to POST /chats/{id}/messages
  if (chat.type === 'dm') {
    const agent = agentById(chat.agentIds[0]);
    if (agent) await agentReply(chat, agent);
  } else {
    const shuffled = [...chat.agentIds].sort(() => Math.random() - 0.5);
    for (const id of shuffled) {
      const agent = agentById(id);
      if (agent) await agentReply(chat, agent, 500 + Math.random() * 1000);
    }
  }
}

async function agentReply(chat, agent, extraDelay = 0) {
  await delay(700 + extraDelay);
  showTyping(agent);
  await delay(800 + Math.random() * 700);
  hideTyping();

  chat.messages.push({ sender: agent.id, text: mockReply(agent), ts: new Date().toISOString() });
  saveState();
  renderMessages(chat);
}

// ── MODAL: DM ────────────────────────────────────────────────────────────────
function renderDMModal() {
  document.getElementById('dm-agent-list').innerHTML = AGENTS.map(a => `
    <div class="modal-agent-item" data-id="${a.id}">
      <div class="avatar-sm avatar-${a.type === 'fiction' ? 'fiction' : 'realw'}">${a.initials}</div>
      <div class="modal-agent-info">
        <div class="modal-agent-name">${escHtml(a.name)}</div>
        <div class="modal-agent-source">${escHtml(a.source)}</div>
      </div>
      <span class="badge ${a.type === 'fiction' ? 'badge-fiction' : 'badge-realworld'}">
        ${a.type === 'fiction' ? 'Fiction' : 'Real'}
      </span>
    </div>`).join('');

  document.getElementById('dm-agent-list').querySelectorAll('.modal-agent-item').forEach(item => {
    item.addEventListener('click', () => startDM(item.dataset.id));
  });
}

// ── MODAL: GROUP ─────────────────────────────────────────────────────────────
let selectedGroupAgents = new Set();

function renderGroupModal() {
  selectedGroupAgents.clear();
  document.getElementById('group-topic').value = '';

  document.getElementById('group-agent-list').innerHTML = AGENTS.map(a => `
    <div class="modal-agent-item" data-id="${a.id}">
      <div class="avatar-sm avatar-${a.type === 'fiction' ? 'fiction' : 'realw'}">${a.initials}</div>
      <div class="modal-agent-info">
        <div class="modal-agent-name">${escHtml(a.name)}</div>
        <div class="modal-agent-source">${escHtml(a.source)}</div>
      </div>
      <span class="badge ${a.type === 'fiction' ? 'badge-fiction' : 'badge-realworld'}">
        ${a.type === 'fiction' ? 'Fiction' : 'Real'}
      </span>
    </div>`).join('');

  document.getElementById('group-agent-list').querySelectorAll('.modal-agent-item').forEach(item => {
    item.addEventListener('click', () => {
      const id = item.dataset.id;
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

// ── AUTO-RESIZE TEXTAREA ─────────────────────────────────────────────────────
function autoResize(ta) {
  ta.style.height = 'auto';
  ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
}

// ── EVENTS ───────────────────────────────────────────────────────────────────
function bindEvents() {
  document.getElementById('login-form').addEventListener('submit', e => {
    e.preventDefault();
    const slug = document.getElementById('user-slug').value.trim();
    if (!slug) return;
    state.user = slug;
    saveState();
    renderHomeScreen();
    showScreen('screen-home');
  });

  document.getElementById('logout-btn').addEventListener('click', () => {
    state.user = null;
    state.activeChatId = null;
    saveState();
    showScreen('screen-login');
  });

  document.getElementById('back-btn').addEventListener('click', () => {
    renderHomeScreen();
    showScreen('screen-home');
  });

  ['new-dm-btn', 'new-dm-btn-2'].forEach(id => {
    document.getElementById(id).addEventListener('click', () => {
      renderDMModal();
      openModal('modal-dm');
    });
  });

  ['new-group-btn', 'new-group-btn-2'].forEach(id => {
    document.getElementById(id).addEventListener('click', () => {
      renderGroupModal();
      openModal('modal-group');
    });
  });

  document.getElementById('close-dm-modal').addEventListener('click', () => closeModal('modal-dm'));
  document.getElementById('close-group-modal').addEventListener('click', () => closeModal('modal-group'));
  document.getElementById('cancel-group-btn').addEventListener('click', () => closeModal('modal-group'));

  document.querySelectorAll('.modal-backdrop').forEach(bd => {
    bd.addEventListener('click', () => { closeModal('modal-dm'); closeModal('modal-group'); });
  });

  document.getElementById('start-group-btn').addEventListener('click', () => {
    const topic = document.getElementById('group-topic').value.trim();
    if (!topic || !selectedGroupAgents.size) return;
    startGroup([...selectedGroupAgents], topic);
  });

  document.getElementById('msg-form').addEventListener('submit', e => {
    e.preventDefault();
    const input = document.getElementById('msg-input');
    const text = input.value;
    input.value = '';
    autoResize(input);
    sendMessage(text);
  });

  const msgInput = document.getElementById('msg-input');
  msgInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      document.getElementById('msg-form').dispatchEvent(new Event('submit'));
    }
  });
  msgInput.addEventListener('input', e => autoResize(e.target));
}

// ── INIT ─────────────────────────────────────────────────────────────────────
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
