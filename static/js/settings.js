import {
  getConfig,
  updateConfig,
  getPagers,
  createPager,
  updatePager,
  deletePager
} from './api.js';

const el = (id) => document.querySelector(`[data-element-id="${id}"]`);

const elements = {
  frequency: null,
  baudRate: null,
  power: null,
  gain: null,
  sampleRate: null,
  saveButton: null,
  addressBookBody: null,
  newPagerName: null,
  newPagerRic: null,
  newPagerNotes: null,
  addPagerButton: null
};

let pagers = [];
let editingId = null;

function notifyPagersChanged() {
  window.dispatchEvent(new CustomEvent('pagers:changed'));
}

function reportError(message) {
  window.dispatchEvent(new CustomEvent('pisag:error', { detail: message }));
}

function showSuccess(message) {
  window.dispatchEvent(new CustomEvent('pisag:toast', { detail: message }));
}

function validateConfig(values) {
  const frequency = values.frequency_mhz ?? values.frequency;
  const power = values.power_dbm ?? values.power;
  const gain = values.gain_db ?? values.gain;
  const sampleRate = values.sample_rate ?? values.sampleRate;

  if (frequency <= 0 || frequency < 100 || frequency > 1000) {
    throw new Error('Frequency should be between 100 and 1000 MHz.');
  }
  if (power < 0 || power > 15) {
    throw new Error('Power must be between 0 and 15 dBm.');
  }
  if (gain < 0 || gain > 47) {
    throw new Error('Gain must be between 0 and 47 dB.');
  }
  if (sampleRate <= 0) {
    throw new Error('Sample rate must be positive.');
  }
}

function validatePager({ name, ric }) {
  if (!name || !name.trim()) {
    throw new Error('Pager name is required.');
  }
  if (!/^[0-9]{7}$/.test(ric)) {
    throw new Error('RIC must be 7 digits.');
  }
  const duplicate = pagers.find((p) => p.id !== editingId && (p.ric_address || p.ric) === ric);
  if (duplicate) {
    throw new Error('RIC must be unique.');
  }
}

async function loadConfig() {
  try {
    const config = await getConfig();
    elements.frequency.value = config.frequency_mhz ?? config.frequency ?? '';
    elements.baudRate.value = config.baud_rate ?? '';
    elements.power.value = config.power_dbm ?? config.power ?? '';
    elements.gain.value = config.gain_db ?? config.gain ?? '';
    elements.sampleRate.value = config.sample_rate ?? '';
  } catch (err) {
    reportError(err.message || 'Failed to load configuration');
  }
}

function renderPagers(list) {
  elements.addressBookBody.innerHTML = '';
  list.forEach((pager) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${pager.name || 'Unnamed'}</td>
      <td>${pager.ric_address || pager.ric || ''}</td>
      <td>${pager.notes || ''}</td>
      <td>
        <span class="action-link" data-action="edit" data-id="${pager.id}">Edit</span> |
        <span class="action-link" data-action="delete" data-id="${pager.id}">Delete</span>
      </td>
    `;
    elements.addressBookBody.appendChild(row);
  });
}

async function loadPagers() {
  try {
    pagers = await getPagers();
    renderPagers(pagers);
  } catch (err) {
    reportError(err.message || 'Failed to load pagers');
  }
}

async function saveConfig() {
  try {
    const values = {
      frequency_mhz: Number(elements.frequency.value),
      baud_rate: Number(elements.baudRate.value),
      power_dbm: Number(elements.power.value),
      gain_db: Number(elements.gain.value),
      sample_rate: Number(elements.sampleRate.value)
    };
    validateConfig(values);
    await updateConfig(values);
    showSuccess('Configuration saved');
  } catch (err) {
    reportError(err.message || 'Failed to save configuration');
  }
}

async function handleAddOrUpdatePager() {
  try {
    const pager = {
      name: elements.newPagerName.value.trim(),
      ric: elements.newPagerRic.value.trim(),
      notes: elements.newPagerNotes.value.trim()
    };
    validatePager(pager);

    if (editingId) {
      await updatePager(editingId, pager.name, pager.ric, pager.notes);
      showSuccess('Pager updated');
    } else {
      await createPager(pager.name, pager.ric, pager.notes);
      showSuccess('Pager added');
    }
    resetPagerForm();
    await loadPagers();
    notifyPagersChanged();
  } catch (err) {
    reportError(err.message || 'Failed to save pager');
  }
}

function resetPagerForm() {
  editingId = null;
  elements.newPagerName.value = '';
  elements.newPagerRic.value = '';
  elements.newPagerNotes.value = '';
  elements.addPagerButton.textContent = 'Add Pager';
}

function startEditPager(id) {
  const pager = pagers.find((p) => String(p.id) === String(id));
  if (!pager) return;
  editingId = pager.id;
  elements.newPagerName.value = pager.name || '';
  elements.newPagerRic.value = pager.ric_address || pager.ric || '';
  elements.newPagerNotes.value = pager.notes || '';
  elements.addPagerButton.textContent = 'Update Pager';
}

async function handleDeletePager(id) {
  const pager = pagers.find((p) => String(p.id) === String(id));
  const name = pager?.name || 'this pager';
  // Confirmation ensures user intent before destructive delete.
  if (!window.confirm(`Delete ${name}? This cannot be undone.`)) return;
  try {
    await deletePager(id);
    await loadPagers();
    notifyPagersChanged();
  } catch (err) {
    reportError(err.message || 'Failed to delete pager');
  }
}

function bindEvents() {
  elements.saveButton.addEventListener('click', (e) => {
    e.preventDefault();
    saveConfig();
  });

  elements.addPagerButton.addEventListener('click', (e) => {
    e.preventDefault();
    handleAddOrUpdatePager();
  });

  elements.addressBookBody.addEventListener('click', (e) => {
    const target = e.target.closest('[data-action]');
    if (!target) return;
    const id = target.getAttribute('data-id');
    const action = target.getAttribute('data-action');
    if (action === 'edit') {
      startEditPager(id);
    } else if (action === 'delete') {
      handleDeletePager(id);
    }
  });
}

export async function init() {
  elements.frequency = el('frequency-input');
  elements.baudRate = el('baud-rate-select');
  elements.power = el('power-input');
  elements.gain = el('gain-input');
  elements.sampleRate = el('sample-rate-input');
  elements.saveButton = el('save-system-config');
  elements.addressBookBody = el('address-book-body');
  elements.newPagerName = el('new-pager-name');
  elements.newPagerRic = el('new-pager-ric');
  elements.newPagerNotes = el('new-pager-notes');
  elements.addPagerButton = el('add-pager-button');

  bindEvents();
  await Promise.all([loadConfig(), loadPagers()]);
}

export async function refreshPagers() {
  await loadPagers();
}
