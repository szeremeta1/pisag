import * as dashboard from './dashboard.js';
import * as send from './send.js';
import * as history from './history.js';
import * as settings from './settings.js';
import { socket } from './socket.js';

const tabButtons = () => Array.from(document.querySelectorAll('.tab-button'));
const tabContents = () => Array.from(document.querySelectorAll('[data-tab-content]'));

let currentTab = 'dashboard';
let errorTimer = null;
const errorBanner = document.getElementById('error-banner');

function hideError() {
  if (!errorBanner) return;
  errorBanner.classList.add('hidden');
  errorBanner.textContent = '';
  if (errorTimer) {
    clearTimeout(errorTimer);
    errorTimer = null;
  }
}

function showError(message) {
  if (!errorBanner) return;
  errorBanner.textContent = message;
  errorBanner.classList.remove('hidden');
  if (errorTimer) clearTimeout(errorTimer);
  errorTimer = setTimeout(hideError, 10000);
}

function handleCustomEvents() {
  window.addEventListener('pisag:error', (e) => {
    showError(e.detail || 'An error occurred');
  });
  window.addEventListener('pisag:toast', (e) => {
    showError(e.detail || 'Saved');
    setTimeout(hideError, 2000);
  });
}

function switchToTab(tabName) {
  currentTab = tabName;
  tabButtons().forEach((btn) => {
    const isActive = btn.dataset.tab === tabName;
    btn.classList.toggle('active', isActive);
  });

  tabContents().forEach((content) => {
    const isActive = content.dataset.tabContent === tabName;
    content.classList.toggle('hidden', !isActive);
  });

  refreshCurrentTab();
}

function refreshCurrentTab() {
  if (currentTab === 'dashboard') dashboard.refresh();
  if (currentTab === 'history') history.refresh();
  if (currentTab === 'settings') settings.refreshPagers?.();
}

function bindTabs() {
  tabButtons().forEach((btn) => {
    btn.addEventListener('click', () => switchToTab(btn.dataset.tab));
  });
}

function bindSocketStatus() {
  socket.on('disconnect', () => {
    showError('Connection lost. Reconnecting...');
  });
  socket.on('connect', () => {
    hideError();
    refreshCurrentTab();
  });
}

function bindGlobalErrors() {
  window.addEventListener('unhandledrejection', (event) => {
    showError(event.reason?.message || 'Unexpected error');
  });
}

async function initApp() {
  bindTabs();
  bindSocketStatus();
  bindCustomEvents();
  bindGlobalErrors();

  await dashboard.init();
  await send.init();
  await history.init();
  await settings.init();
}

function bindCustomEvents() {
  handleCustomEvents();
}

document.addEventListener('DOMContentLoaded', () => {
  switchToTab('dashboard');
  initApp();
});

export const getCurrentTab = () => currentTab;
export { switchToTab, showError, hideError };
