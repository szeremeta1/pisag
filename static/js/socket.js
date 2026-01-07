const socket = io();

const listeners = {
  message_queued: [],
  encoding_started: [],
  transmitting: [],
  transmission_complete: [],
  transmission_failed: [],
  status_update: [],
  history_update: [],
  analytics_update: []
};

function register(event, callback) {
  if (listeners[event]) {
    listeners[event].push(callback);
  }
}

function emitToListeners(event, payload) {
  if (!listeners[event]) return;
  listeners[event].forEach((cb) => {
    try {
      cb(payload);
    } catch (err) {
      console.error(`Listener error for ${event}`, err);
    }
  });
}

socket.on('connect', () => {
  socket.emit('subscribe_updates');
});

socket.on('disconnect', () => {});

socket.on('message_queued', (data) => emitToListeners('message_queued', data));
socket.on('encoding_started', (data) => emitToListeners('encoding_started', data));
socket.on('transmitting', (data) => emitToListeners('transmitting', data));
socket.on('transmission_complete', (data) => emitToListeners('transmission_complete', data));
socket.on('transmission_failed', (data) => emitToListeners('transmission_failed', data));
socket.on('status_update', (data) => emitToListeners('status_update', data));
socket.on('history_update', (data) => emitToListeners('history_update', data));
socket.on('analytics_update', (data) => emitToListeners('analytics_update', data));

export { socket };
export const onMessageQueued = (cb) => register('message_queued', cb);
export const onEncodingStarted = (cb) => register('encoding_started', cb);
export const onTransmitting = (cb) => register('transmitting', cb);
export const onTransmissionComplete = (cb) => register('transmission_complete', cb);
export const onTransmissionFailed = (cb) => register('transmission_failed', cb);
export const onStatusUpdate = (cb) => register('status_update', cb);
export const onHistoryUpdate = (cb) => register('history_update', cb);
export const onAnalyticsUpdate = (cb) => register('analytics_update', cb);
