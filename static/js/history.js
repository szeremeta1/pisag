import { getMessages, resendMessage } from './api.js';
import { onHistoryUpdate } from './socket.js';

const el = (id) => document.querySelector(`[data-element-id="${id}"]`);

let state = {
  page: 1,
  pageSize: 10,
  total: 0,
  totalKnown: false,
  hasNext: false
};

const elements = {
  tableBody: null,
  pagination: null,
  refreshBtn: null
};

function reportError(message) {
  window.dispatchEvent(new CustomEvent('pisag:error', { detail: message }));
}

function formatTimestamp(value) {
  if (!value) return '--';
  const date = new Date(value);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${date.toLocaleTimeString([], { hour12: false })}`;
}

function formatRecipients(msg) {
  if (Array.isArray(msg.recipients)) {
    if (msg.recipients.length === 1) {
      const r = msg.recipients[0];
      return r.name ? `${r.name} (${r.ric_address || r.ric})` : (r.ric_address || r.ric || 'Unknown');
    }
    return `Broadcast (${msg.recipients.length} pagers)`;
  }
  if (msg.recipient_name && msg.ric_address) {
    return `${msg.recipient_name} (${msg.ric_address})`;
  }
  return msg.ric_address || msg.ric || 'Unknown';
}

function formatType(msg) {
  const type = msg.message_type || msg.type;
  if (!type) return '--';
  return type.toLowerCase() === 'numeric' ? 'Numeric' : 'Alpha';
}

function formatFrequency(value) {
  if (!value && value !== 0) return '--';
  return `${Number(value).toFixed(4)} MHz`;
}

function formatDuration(value) {
  if (!value && value !== 0) return 'N/A';
  return `${Number(value).toFixed(1)}s`;
}

function formatStatus(msg) {
  const status = msg.status || msg.state;
  const success = status === 'success' || status === 'completed';
  const text = success ? '✓ Success' : '✗ Failed';
  const cls = success ? 'status-success' : 'status-failed';
  return `<span class="${cls}">${text}</span>`;
}

function truncate(text = '', max = 50) {
  if (text.length <= max) return text;
  return `${text.slice(0, max)}…`;
}

function renderRows(messages) {
  elements.tableBody.innerHTML = '';
  messages.forEach((msg) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${formatTimestamp(msg.created_at || msg.timestamp)}</td>
      <td>${formatRecipients(msg)}</td>
      <td>${truncate(msg.message_text || msg.message, 50)}</td>
      <td>${formatType(msg)}</td>
      <td>${formatFrequency(msg.frequency_mhz || msg.frequency)}</td>
      <td>${formatDuration(msg.duration_seconds || msg.duration)}</td>
      <td>${formatStatus(msg)}</td>
      <td><span class="action-link" data-action="resend" data-id="${msg.id}">Resend</span></td>
    `;
    elements.tableBody.appendChild(row);
  });
}

function renderPagination() {
  const totalPages = state.totalKnown
    ? Math.max(1, Math.ceil(state.total / state.pageSize))
    : state.page + (state.hasNext ? 1 : 0);
  elements.pagination.innerHTML = '';

  const makeBtn = (label, page, disabled, active = false) => {
    const btn = document.createElement('button');
    btn.textContent = label;
    if (disabled) btn.disabled = true;
    if (active) btn.classList.add('active');
    btn.addEventListener('click', () => changePage(page));
    elements.pagination.appendChild(btn);
  };

  makeBtn('Previous', Math.max(1, state.page - 1), state.page === 1);
  for (let p = 1; p <= totalPages; p += 1) {
    makeBtn(String(p), p, false, p === state.page);
  }
  if (totalPages >= 1) {
    const disableNext = state.totalKnown ? state.page === totalPages : !state.hasNext;
    makeBtn('Next', state.page + 1, disableNext);
  }
}

async function loadHistory(offset = 0, limit = 10) {
  try {
    const result = await getMessages(offset, limit);
    const messages = result?.messages || result || [];
    const total = result?.total ?? result?.count;
    state.totalKnown = Number.isFinite(total);
    state.total = state.totalKnown ? total : offset + messages.length;
    state.hasNext = state.totalKnown ? offset + messages.length < state.total : messages.length === state.pageSize;
    renderRows(messages);
    renderPagination();
  } catch (err) {
    reportError(err.message || 'Failed to load history');
  }
}

function changePage(page) {
  state.page = page;
  const offset = (state.page - 1) * state.pageSize;
  loadHistory(offset, state.pageSize);
}

async function handleResend(id) {
  try {
    await resendMessage(id);
    loadHistory((state.page - 1) * state.pageSize, state.pageSize);
  } catch (err) {
    reportError(err.message || 'Failed to resend message');
  }
}

function bindEvents() {
  elements.tableBody.addEventListener('click', (e) => {
    const target = e.target.closest('[data-action="resend"]');
    if (!target) return;
    const id = target.getAttribute('data-id');
    handleResend(id);
  });

  elements.refreshBtn.addEventListener('click', () => {
    loadHistory((state.page - 1) * state.pageSize, state.pageSize);
  });
}

function bindSocket() {
  onHistoryUpdate(() => {
    loadHistory((state.page - 1) * state.pageSize, state.pageSize);
  });
}

export async function init() {
  elements.tableBody = el('history-table-body');
  elements.pagination = el('pagination-controls');
  elements.refreshBtn = el('refresh-history');

  bindEvents();
  bindSocket();
  await loadHistory(0, state.pageSize);
}

export function refresh() {
  loadHistory((state.page - 1) * state.pageSize, state.pageSize);
}
