/**
 * EcoSentinel API Client
 * Connects the React dashboard to Person 3's shared reasoning pipeline.
 */

export function getApiBaseUrl() {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('ecosentinel_api_url');
    if (saved && saved.trim()) return saved.trim().replace(/\/+$/, '');
  }
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && envUrl.trim()) return envUrl.trim().replace(/\/+$/, '');

  // If deployed on Render or elsewhere, attempt connecting to default Render backend
  if (typeof window !== 'undefined' && window.location.hostname.includes('onrender.com')) {
    return 'https://ecosentinel-backend.onrender.com';
  }

  return 'http://localhost:8000';
}

export function setApiBaseUrl(url) {
  if (typeof window !== 'undefined') {
    if (!url || !url.trim()) {
      localStorage.removeItem('ecosentinel_api_url');
    } else {
      localStorage.setItem('ecosentinel_api_url', url.trim().replace(/\/+$/, ''));
    }
  }
}

async function request(endpoint, options = {}) {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${endpoint}`;
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

    const text = await res.text();
    // Guard against HTML returned by SPA catch-all routers (e.g. index.html)
    if (text.trim().startsWith('<') || text.trim().startsWith('<!doctype') || text.trim().startsWith('<!DOCTYPE')) {
      throw new Error(
        `Backend returned HTML instead of JSON. Ensure the backend API URL is configured (currently: ${baseUrl}).`
      );
    }

    return JSON.parse(text);
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

export async function simulatePoaching() {
  return request('/demo/fake-poaching', {
    method: 'POST',
  });
}

export async function triggerLiveOcean(mode = 'auto', limit = 5) {
  return request(`/demo/live-ocean?mode=${mode}&limit=${limit}`, {
    method: 'POST',
  });
}

export async function getOceanIngestStatus() {
  return request('/ingest/ocean/status');
}

export async function triggerOceanIngest(mode = 'auto', limit = 10) {
  return request(`/ingest/ocean?mode=${mode}&limit=${limit}`, {
    method: 'POST',
  });
}
