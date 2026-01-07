import { getPagers, sendMessage } from './api.js';
import {
  onMessageQueued,
  onEncodingStarted,
  onTransmitting,
  onTransmissionComplete,
  onTransmissionFailed
} from './socket.js';

const el = (id) => document.querySelector(`[data-element-id="${id}"]`);

const elements = {
  individualSelect: null,
  individualRic: null,
  individualType: null,
  individualText: null,
  individualButton: null,
  individualProgress: null,
  individualProgressBar: null,
  individualProgressText: null,
  individualSuccess: null,
  broadcastCheckboxes: null,
  broadcastRic: null,
  broadcastType: null,
  broadcastText: null,
  broadcastButton: null,
  broadcastProgress: null,
  broadcastProgressBar: null,
  broadcastProgressText: null,
  broadcastSuccess: null
};

let pagers = [];
let activeForm = null;

function reportError(message) {
  window.dispatchEvent(new CustomEvent('pisag:error', { detail: message }));
}

function showProgress(form, percent, text) {
  const bar = form === 'individual' ? elements.individualProgressBar : elements.broadcastProgressBar;
  const container = form === 'individual' ? elements.individualProgress : elements.broadcastProgress;
  const label = form === 'individual' ? elements.individualProgressText : elements.broadcastProgressText;

  if (!bar || !container || !label) return;
  container.classList.remove('hidden');
  bar.style.width = `${percent}%`;
  label.textContent = text;
}

function hideProgress(form) {
  const container = form === 'individual' ? elements.individualProgress : elements.broadcastProgress;
  if (container) container.classList.add('hidden');
}

function showSuccess(form, message) {
  const box = form === 'individual' ? elements.individualSuccess : elements.broadcastSuccess;
  if (!box) return;
  box.textContent = message;
  box.classList.remove('hidden');
  setTimeout(() => box.classList.add('hidden'), 3000);
}

function toggleButton(form, disabled) {
  const button = form === 'individual' ? elements.individualButton : elements.broadcastButton;
  if (button) button.disabled = disabled;
}

function validateRic(value) {
  return /^[0-9]{7}$/.test(value);
}

function validateMessage(text) {
  return text && text.trim().length > 0;
}

function validateLength(text, type) {
  if (type === 'alphanumeric') {
    return text.length <= 80;
  }
  return text.length <= 120;
}

function getSelectedPagersRic() {
  return Array.from(elements.broadcastCheckboxes.querySelectorAll('input[type="checkbox"]:checked')).map((c) => c.value);
}

function populatePagers(list) {
  elements.individualSelect.innerHTML = '<option value="">-- Select from address book --</option>';
  elements.broadcastCheckboxes.innerHTML = '';

  list.forEach((pager) => {
    const option = document.createElement('option');
    option.value = pager.ric_address || pager.ric;
    option.textContent = pager.name ? `${pager.name} (RIC: ${pager.ric_address || pager.ric})` : (pager.ric_address || pager.ric);
    elements.individualSelect.appendChild(option);

    const label = document.createElement('label');
    label.style.display = 'block';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.value = pager.ric_address || pager.ric;
    checkbox.id = `broadcast-${checkbox.value}`;
    const span = document.createElement('span');
    span.textContent = option.textContent;
    label.appendChild(checkbox);
    label.appendChild(span);
    elements.broadcastCheckboxes.appendChild(label);
  });
}

async function loadPagers() {
  try {
    pagers = await getPagers();
    populatePagers(pagers);
  } catch (err) {
    reportError(err.message || 'Failed to load pagers');
  }
}

function collectIndividualPayload() {
  const selected = elements.individualSelect.value;
  const manualRic = elements.individualRic.value.trim();
  const ric = manualRic || selected;
  const messageType = elements.individualType.value;
  const messageText = elements.individualText.value.trim();

  if (!ric || !validateRic(ric)) {
    throw new Error('Enter a valid 7-digit RIC address.');
  }
  if (!validateMessage(messageText)) {
    throw new Error('Message is required.');
  }
  if (!validateLength(messageText, messageType)) {
    throw new Error('Message exceeds allowed length.');
  }

  return { recipients: [ric], messageText, messageType };
}

function collectBroadcastPayload() {
  const checked = getSelectedPagersRic();
  const manual = elements.broadcastRic.value
    .split(',')
    .map((v) => v.trim())
    .filter(Boolean);
  const recipients = [...checked, ...manual];
  const messageType = elements.broadcastType.value;
  const messageText = elements.broadcastText.value.trim();

  if (!recipients.length) {
    throw new Error('Select at least one recipient.');
  }
  const invalid = recipients.find((r) => !validateRic(r));
  if (invalid) {
    throw new Error(`Invalid RIC: ${invalid}`);
  }
  if (!validateMessage(messageText)) {
    throw new Error('Message is required.');
  }
  if (!validateLength(messageText, messageType)) {
    throw new Error('Message exceeds allowed length.');
  }

  return { recipients, messageText, messageType };
}

async function handleIndividualSubmit() {
  try {
    const payload = collectIndividualPayload();
    activeForm = 'individual';
    toggleButton('individual', true);
    showProgress('individual', 0, 'Queued...');
    await sendMessage(payload.recipients, payload.messageText, payload.messageType);
    showSuccess('individual', 'Message sent successfully.');
    elements.individualText.value = '';
    hideProgress('individual');
  } catch (err) {
    reportError(err.message || 'Failed to send message');
  } finally {
    toggleButton('individual', false);
  }
}

async function handleBroadcastSubmit() {
  try {
    const payload = collectBroadcastPayload();
    activeForm = 'broadcast';
    toggleButton('broadcast', true);
    showProgress('broadcast', 0, 'Queued...');
    await sendMessage(payload.recipients, payload.messageText, payload.messageType);
    showSuccess('broadcast', `Broadcast sent to ${payload.recipients.length} recipient(s).`);
    elements.broadcastText.value = '';
    elements.broadcastRic.value = '';
    elements.broadcastCheckboxes.querySelectorAll('input[type="checkbox"]').forEach((c) => (c.checked = false));
    hideProgress('broadcast');
  } catch (err) {
    reportError(err.message || 'Failed to send broadcast');
  } finally {
    toggleButton('broadcast', false);
  }
}

function bindForms() {
  elements.individualButton.addEventListener('click', (e) => {
    e.preventDefault();
    handleIndividualSubmit();
  });

  elements.broadcastButton.addEventListener('click', (e) => {
    e.preventDefault();
    handleBroadcastSubmit();
  });
}

function bindSocketProgress() {
  onMessageQueued(() => {
    if (!activeForm) return;
    showProgress(activeForm, 0, 'Queued...');
  });
  onEncodingStarted(() => {
    if (!activeForm) return;
    showProgress(activeForm, 33, 'Encoding...');
  });
  onTransmitting(() => {
    if (!activeForm) return;
    showProgress(activeForm, 66, 'Transmitting...');
  });
  onTransmissionComplete(() => {
    if (!activeForm) return;
    showProgress(activeForm, 100, 'Complete');
    setTimeout(() => hideProgress(activeForm), 1500);
    activeForm = null;
  });
  onTransmissionFailed((payload) => {
    if (!activeForm) return;
    reportError(payload?.error || 'Transmission failed');
    hideProgress(activeForm);
    activeForm = null;
  });
}

export async function init() {
  elements.individualSelect = el('individual-pager-select');
  elements.individualRic = el('individual-ric-input');
  elements.individualType = el('individual-message-type');
  elements.individualText = el('individual-message-text');
  elements.individualButton = el('send-individual-button');
  elements.individualProgress = el('individual-progress');
  elements.individualProgressBar = elements.individualProgress?.querySelector('.progress-bar');
  elements.individualProgressText = elements.individualProgress?.querySelector('.progress-text');
  elements.individualSuccess = el('individual-success');

  elements.broadcastCheckboxes = el('broadcast-pager-checkboxes');
  elements.broadcastRic = el('broadcast-ric-input');
  elements.broadcastType = el('broadcast-message-type');
  elements.broadcastText = el('broadcast-message-text');
  elements.broadcastButton = el('send-broadcast-button');
  elements.broadcastProgress = el('broadcast-progress');
  elements.broadcastProgressBar = elements.broadcastProgress?.querySelector('.progress-bar');
  elements.broadcastProgressText = elements.broadcastProgress?.querySelector('.progress-text');
  elements.broadcastSuccess = el('broadcast-success');

  bindForms();
  bindSocketProgress();
  window.addEventListener('pagers:changed', loadPagers);
  await loadPagers();
}

export function clearForms() {
  if (elements.individualSelect) elements.individualSelect.value = '';
  if (elements.individualRic) elements.individualRic.value = '';
  if (elements.individualText) elements.individualText.value = '';
  if (elements.broadcastRic) elements.broadcastRic.value = '';
  if (elements.broadcastText) elements.broadcastText.value = '';
  if (elements.broadcastCheckboxes) {
    elements.broadcastCheckboxes.querySelectorAll('input[type="checkbox"]').forEach((c) => (c.checked = false));
  }
}
