const BASE_URL = '/api';

async function request(method, endpoint, body) {
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json'
    }
  };

  if (body !== undefined) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, options);
  const isJson = response.headers.get('Content-Type')?.includes('application/json');
  let data;
  try {
    data = isJson ? await response.json() : undefined;
  } catch (err) {
    data = undefined;
  }

  if (!response.ok) {
    const message = data?.message || data?.error || `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return data;
}

export async function sendMessage(recipients, messageText, messageType) {
  return request('POST', '/send', {
    recipients,
    message_text: messageText,
    message_type: messageType
  });
}

export async function getMessages(offset = 0, limit = 10) {
  return request('GET', `/messages?offset=${offset}&limit=${limit}`);
}

export async function resendMessage(messageId) {
  return request('POST', `/messages/${messageId}/resend`);
}

export async function getPagers() {
  return request('GET', '/pagers');
}

export async function createPager(name, ricAddress, notes) {
  return request('POST', '/pagers', {
    name,
    ric_address: ricAddress,
    notes
  });
}

export async function updatePager(pagerId, name, ricAddress, notes) {
  return request('PUT', `/pagers/${pagerId}`, {
    name,
    ric_address: ricAddress,
    notes
  });
}

export async function deletePager(pagerId) {
  return request('DELETE', `/pagers/${pagerId}`);
}

export async function getConfig() {
  return request('GET', '/config');
}

export async function updateConfig(config) {
  return request('PUT', '/config', config);
}

export async function getAnalytics() {
  return request('GET', '/analytics');
}

export async function getStatus() {
  return request('GET', '/status');
}
