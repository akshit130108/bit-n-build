/**
 * EcoSentinel API Client
 * Connects the React dashboard to Person 3's shared reasoning pipeline.
 */

const RAW_URL = import.meta.env.VITE_API_URL || 
  (typeof window !== 'undefined' && window.location.port !== '5173' && window.location.hostname !== 'localhost' 
    ? window.location.origin 
    : 'http://localhost:8000');

const API_BASE_URL = RAW_URL.replace(/\/+$/, '');

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const res = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`HTTP ${res.status}: ${errorText || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    console.error(`API error at ${endpoint}:`, err);
    throw err;
  }
}

export async function getHealth() {
  return request('/health');
}

export async function getEvents(params = {}) {
  const query = new URLSearchParams();
  if (params.domain) query.append('domain', params.domain);
  if (params.risk_level) query.append('risk_level', params.risk_level);
  if (params.status) query.append('status', params.status);
  if (params.limit) query.append('limit', params.limit);

  const qs = query.toString();
  return request(`/events${qs ? `?${qs}` : ''}`);
}

export async function getEvent(eventId) {
  return request(`/events/${eventId}`);
}

export async function approveEvent(eventId, reviewer = 'ranger_supervisor', notes = 'Action approved from dashboard') {
  return request(`/events/${eventId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ reviewer, notes }),
  });
}

export async function rejectEvent(eventId, reviewer = 'ranger_supervisor', notes = 'Action rejected from dashboard') {
  return request(`/events/${eventId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reviewer, notes }),
  });
}

export async function requestMoreEvidence(eventId, reviewer = 'ranger_supervisor', notes = 'Requesting additional sensor verification') {
  return request(`/events/${eventId}/request-more-evidence`, {
    method: 'POST',
    body: JSON.stringify({ reviewer, notes }),
  });
}

export async function simulateLand() {
  return request('/demo/fake-land', {
    method: 'POST',
  });
}

export async function simulateOcean() {
  return request('/demo/fake-ocean', {
    method: 'POST',
  });
}

export async function seedRecurrence() {
  return request('/demo/seed-recurrence', {
    method: 'POST',
  });
}
