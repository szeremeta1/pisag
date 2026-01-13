import {
  getConfig,
  getEncoders,
  updateConfig,
  getPagers,
  createPager,
  updatePager,
  deletePager
} from './api.js';

const el = (id) => document.querySelector(`[data-element-id="${id}"]`);

// Encoder short names to full class path mapping
const ENCODER_CLASS_MAP = {
  'gr_pocsag': 'pisag.plugins.encoders.gr_pocsag.GrPocsagEncoder',
  'pure_python': 'pisag.plugins.encoders.pure_python.PurePythonEncoder'
};

// Reverse mapping from class path to short name
const ENCODER_SHORT_NAME_MAP = Object.fromEntries(
  Object.entries(ENCODER_CLASS_MAP).map(([k, v]) => [v, k])
);

const elements = {
  frequency: null,
  baudRate: null,
  power: null,
  gain: null,
  sampleRate: null,
  encoder: null,
  invertFsk: null,
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

function validateConfig(systemValues) {
  const frequency = systemValues.frequency;
  const power = systemValues.transmit_power;
  const gain = systemValues.if_gain;
  const sampleRate = systemValues.sample_rate;

  if (frequency <= 0 || frequency < 1 || frequency > 6000) {
    throw new Error('Frequency should be between 1 and 6000 MHz.');
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
    const system = config.system || {};
    const pocsag = config.pocsag || {};
    const plugins = config.plugins || {};
    elements.frequency.value = system.frequency ?? '';
    elements.baudRate.value = pocsag.baud_rate ?? '';
    elements.power.value = system.transmit_power ?? '';
    elements.gain.value = system.if_gain ?? '';
    elements.sampleRate.value = system.sample_rate ?? '';
    elements.invertFsk.checked = pocsag.invert ?? false;
    
    // Set encoder selection based on current config
    const currentEncoder = plugins.pocsag_encoder || '';
    const shortName = ENCODER_SHORT_NAME_MAP[currentEncoder] || 'gr_pocsag';
    elements.encoder.value = shortName;
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
      system: {
        frequency: Number(elements.frequency.value),
        transmit_power: Number(elements.power.value),
        if_gain: Number(elements.gain.value),
        sample_rate: Number(elements.sampleRate.value)
      },
      pocsag: {
        baud_rate: Number(elements.baudRate.value),
        invert: elements.invertFsk.checked
      },
      plugins: {
        pocsag_encoder: elements.encoder.value
      }
    };
    validateConfig(values.system);
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
  elements.encoder = el('encoder-select');
  elements.invertFsk = el('invert-fsk-checkbox');
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
