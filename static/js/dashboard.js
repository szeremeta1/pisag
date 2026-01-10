import { getStatus, getAnalytics } from './api.js';
import { onStatusUpdate, onHistoryUpdate, onAnalyticsUpdate } from './socket.js';

const el = (id) => document.querySelector(`[data-element-id="${id}"]`);

const elements = {
  hackrfStatus: null,
  frequency: null,
  baudRate: null,
  transmitPower: null,
  ifGain: null,
  sampleRate: null,
  totalMessages: null,
  successRate: null,
  todayCount: null,
  activePagers: null,
  queueSize: null,
  workerStatus: null,
  recentMessagesBody: null,
  deviation: null,
  fskPolarity: null,
  encoder: null,
  sdrInterface: null
};

function reportError(message) {
  window.dispatchEvent(new CustomEvent('pisag:error', { detail: message }));
}

function formatFrequency(value) {
  if (!value && value !== 0) return '--';
  return `${Number(value).toFixed(4)} MHz`;
}

function formatStatusText(status) {
  if (status === true || status === 'connected') return 'Connected';
  if (status === false || status === 'disconnected') return 'Disconnected';
  return status || 'Unknown';
}

function renderStatus(statusData) {
  if (!elements.hackrfStatus) return;
  const connected = statusData?.hackrf_connected ?? statusData?.healthy;
  const statusText = formatStatusText(connected ? 'Connected' : 'Disconnected');
  elements.hackrfStatus.textContent = statusText;
  elements.hackrfStatus.classList.toggle('status-success', !!connected);
  elements.hackrfStatus.classList.toggle('status-failed', !connected);

  const frequency = statusData?.frequency ?? statusData?.frequency_mhz;
  elements.frequency.textContent = formatFrequency(frequency);
  elements.baudRate.textContent = statusData?.baud_rate || '--';
  
  // Display additional system information
  if (statusData?.transmit_power !== undefined) {
    elements.transmitPower.textContent = `${statusData.transmit_power} dBm`;
  }
  if (statusData?.if_gain !== undefined) {
    elements.ifGain.textContent = `${statusData.if_gain} dB`;
  }
  if (statusData?.sample_rate !== undefined) {
    elements.sampleRate.textContent = `${statusData.sample_rate} MHz`;
  }
  if (statusData?.queue_size !== undefined) {
    elements.queueSize.textContent = statusData.queue_size;
  }
  
  // Worker status
  const workerRunning = statusData?.worker_running;
  if (workerRunning !== undefined) {
    elements.workerStatus.textContent = workerRunning ? 'Running' : 'Stopped';
    elements.workerStatus.classList.toggle('status-success', !!workerRunning);
    elements.workerStatus.classList.toggle('status-failed', !workerRunning);
  }
  
  // System configuration details
  if (statusData?.deviation !== undefined) {
    elements.deviation.textContent = `${statusData.deviation} kHz`;
  }
  if (statusData?.invert !== undefined) {
    elements.fskPolarity.textContent = statusData.invert ? 'Inverted (PDW Compatible)' : 'Normal';
  }
  if (statusData?.encoder) {
    const encoderName = statusData.encoder.split('.').pop();
    elements.encoder.textContent = encoderName;
  }
  if (statusData?.sdr_interface) {
    const sdrName = statusData.sdr_interface.split('.').pop();
    elements.sdrInterface.textContent = sdrName;
  }
}

function renderStats(analytics) {
  const total = analytics?.total_messages ?? 0;
  const successRate = analytics?.success_rate ?? 0;
  const today = analytics?.today_count ?? 0;
  const active = analytics?.active_pagers ?? 0;

  elements.totalMessages.textContent = total;
  elements.successRate.textContent = `${(successRate * 100).toFixed(1)}%`;
  elements.todayCount.textContent = today;
  elements.activePagers.textContent = active;
}

function renderRecentMessages(messages = []) {
  if (!elements.recentMessagesBody) return;
  elements.recentMessagesBody.innerHTML = '';

  messages.slice(0, 10).forEach((msg) => {
    const row = document.createElement('tr');
    const statusSuccess = msg.status === 'success' || msg.status === 'completed';
    row.innerHTML = `
      <td>${formatTime(msg.created_at || msg.timestamp)}</td>
      <td>${formatRecipient(msg)}</td>
      <td>${truncate(msg.message_text || msg.message, 80)}</td>
      <td class="${statusSuccess ? 'status-success' : 'status-failed'}">${statusSuccess ? '✓ Success' : '✗ Failed'}</td>
    `;
    elements.recentMessagesBody.appendChild(row);
  });
}

function truncate(text = '', max = 80) {
  if (text.length <= max) return text;
  return `${text.slice(0, max)}…`;
}

function formatRecipient(msg) {
  if (msg?.recipients && Array.isArray(msg.recipients)) {
    if (msg.recipients.length === 1) {
      const r = msg.recipients[0];
      return r.name ? `${r.name} (${r.ric_address || r.ric})` : (r.ric_address || r.ric || 'Unknown');
    }
    return `Broadcast (${msg.recipients.length} pagers)`;
  }
  if (msg?.recipient_name && msg?.ric_address) {
    return `${msg.recipient_name} (${msg.ric_address})`;
  }
  return msg?.ric_address || msg?.ric || 'Unknown';
}

function formatTime(value) {
  if (!value) return '--';
  const date = new Date(value);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

async function refresh() {
  try {
    const [statusData, analytics] = await Promise.all([getStatus(), getAnalytics()]);
    renderStatus(statusData);
    renderStats(analytics);
    const recent = analytics?.recent_messages || analytics?.messages || [];
    renderRecentMessages(recent);
  } catch (err) {
    reportError(err.message || 'Failed to load dashboard');
  }
}

function bindSockets() {
  onStatusUpdate((payload) => renderStatus(payload));
  onHistoryUpdate(() => refresh());
  onAnalyticsUpdate((payload) => {
    renderStats(payload);
    const recent = payload?.recent_messages || payload?.messages || [];
    renderRecentMessages(recent);
  });
}

export async function init() {
  elements.hackrfStatus = el('hackrf-status');
  elements.frequency = el('frequency');
  elements.baudRate = el('baud-rate');
  elements.transmitPower = el('transmit-power');
  elements.ifGain = el('if-gain');
  elements.sampleRate = el('sample-rate');
  elements.totalMessages = el('total-messages');
  elements.successRate = el('success-rate');
  elements.todayCount = el('today-count');
  elements.activePagers = el('active-pagers');
  elements.queueSize = el('queue-size');
  elements.workerStatus = el('worker-status');
  elements.recentMessagesBody = el('recent-messages-body');
  elements.deviation = el('deviation');
  elements.fskPolarity = el('fsk-polarity');
  elements.encoder = el('encoder');
  elements.sdrInterface = el('sdr-interface');

  bindSockets();
  await refresh();
}

export { refresh };
