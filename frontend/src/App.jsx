import React, { useState, useEffect, useCallback } from 'react';
import MapView from './components/MapView';
import IncidentList from './components/IncidentList';
import IncidentDetails from './components/IncidentDetails';
import PipelineStatus from './components/PipelineStatus';
import {
  getEvents,
  getHealth,
  approveEvent,
  rejectEvent,
  requestMoreEvidence,
  simulateLand,
  simulateOcean,
  seedRecurrence,
  getApiBaseUrl,
  setApiBaseUrl,
} from './api/ecosentinel';

import {
  createMockLandIncident,
  createMockOceanIncident,
  createInitialDemoIncidents,
} from './mockData';

export default function App() {
  const [incidents, setIncidents] = useState(() => createInitialDemoIncidents());
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [loading, setLoading] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [notification, setNotification] = useState(null);
  const [apiError, setApiError] = useState(null);
  const [apiUrl, setApiUrl] = useState(getApiBaseUrl());
  const [inputUrl, setInputUrl] = useState(apiUrl);
  const [showConfig, setShowConfig] = useState(false);

  // Set initial selected incident from demo data
  useEffect(() => {
    if (!selectedIncident && incidents.length > 0) {
      setSelectedIncident(incidents[0]);
    }
  }, [incidents, selectedIncident]);

  const showNotification = (message, type = 'info') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4500);
  };

  // Fetch all incidents from GET /events
  const fetchIncidents = useCallback(async (isInitial = false) => {
    if (isInitial) setLoading(true);
    try {
      const data = await getEvents({ limit: 100 });
      if (Array.isArray(data) && data.length > 0) {
        setIncidents(data);
      }
      setBackendOnline(true);
      setApiError(null);
      setLastUpdated(new Date());

      setSelectedIncident((prev) => {
        if (!prev && data.length > 0) return data[0];
        if (prev) {
          const updated = data.find((d) => d.event?.id === prev.event?.id);
          return updated || prev;
        }
        return prev;
      });
    } catch (err) {
      setBackendOnline(false);
      setApiError(err.message || 'Connecting to EcoSentinel backend...');
    } finally {
      if (isInitial) setLoading(false);
    }
  }, []);

  // Poll GET /events every 4 seconds
  useEffect(() => {
    fetchIncidents(true);
    const interval = setInterval(() => {
      fetchIncidents(false);
    }, 4000);
    return () => clearInterval(interval);
  }, [fetchIncidents]);

  // Demo Handlers
  const handleSimulateLand = async () => {
    try {
      setActionLoading(true);
      if (!backendOnline) {
        const mock = createMockLandIncident();
        setIncidents((prev) => [mock, ...prev]);
        setSelectedIncident(mock);
        showNotification(`Simulated Chainsaw incident [${mock.event.id}] (Demo Mode)`, 'success');
        return;
      }
      const res = await simulateLand();
      showNotification(`Simulated Chainsaw event [${res.event?.id}] processed: ${res.classification?.refined_type}`, 'success');
      await fetchIncidents(false);
      setSelectedIncident(res);
    } catch (err) {
      const mock = createMockLandIncident();
      setIncidents((prev) => [mock, ...prev]);
      setSelectedIncident(mock);
      showNotification(`Backend offline / sleeping — simulated Chainsaw event in Demo Mode`, 'warning');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSimulateOcean = async () => {
    try {
      setActionLoading(true);
      if (!backendOnline) {
        const mock = createMockOceanIncident();
        setIncidents((prev) => [mock, ...prev]);
        setSelectedIncident(mock);
        showNotification(`Simulated Dark Vessel incident [${mock.event.id}] (Demo Mode)`, 'success');
        return;
      }
      const res = await simulateOcean();
      showNotification(`Simulated Dark Vessel event [${res.event?.id}] processed: ${res.classification?.refined_type}`, 'success');
      await fetchIncidents(false);
      setSelectedIncident(res);
    } catch (err) {
      const mock = createMockOceanIncident();
      setIncidents((prev) => [mock, ...prev]);
      setSelectedIncident(mock);
      showNotification(`Backend offline / sleeping — simulated Dark Vessel event in Demo Mode`, 'warning');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSeedRecurrence = async () => {
    try {
      setActionLoading(true);
      if (!backendOnline) {
        const spike = createMockLandIncident();
        spike.risk.score = 96;
        spike.risk.level = 'CRITICAL';
        spike.memory.recurrence_detected = true;
        spike.memory.historical_matches_count = 4;
        spike.memory.pattern_summary = 'Recurrence surge: 4 illegal chainsaw detections clustered in 12h.';
        spike.pipeline_trajectory[5].detail = 'Risk surged to CRITICAL (96/100) due to 4 historical recurrence matches.';
        setIncidents((prev) => [spike, ...prev]);
        setSelectedIncident(spike);
        showNotification(`Recurrence Spike Demonstrated! Risk score surged to 96/100 (CRITICAL)`, 'warning');
        return;
      }
      const res = await seedRecurrence();
      const trigger = res.new_trigger_incident;
      showNotification(`Recurrence Spike Demonstrated! 3 seeded incidents caused Risk score to surge to ${trigger.risk?.score}/100`, 'warning');
      await fetchIncidents(false);
      setSelectedIncident(trigger);
    } catch (err) {
      const spike = createMockLandIncident();
      spike.risk.score = 96;
      spike.risk.level = 'CRITICAL';
      setIncidents((prev) => [spike, ...prev]);
      setSelectedIncident(spike);
      showNotification(`Recurrence Spike Demonstrated (Demo Mode)`, 'warning');
    } finally {
      setActionLoading(false);
    }
  };

  // Approval Handlers
  const handleApprove = async (id, reviewer, notes) => {
    try {
      setActionLoading(true);
      if (!backendOnline) {
        setIncidents((prev) =>
          prev.map((inc) => {
            if (inc.event?.id === id) {
              const updated = {
                ...inc,
                human_gate: { ...inc.human_gate, status: 'APPROVED', reviewer, notes },
                action: { ...inc.action, status: 'DISPATCHED' },
              };
              setSelectedIncident(updated);
              return updated;
            }
            return inc;
          })
        );
        showNotification(`Incident ${id} APPROVED (Demo Mode). Action dispatched.`, 'success');
        return;
      }
      const updated = await approveEvent(id, reviewer, notes);
      showNotification(`Incident ${id} APPROVED. Action dispatched: ${updated.action?.action}`, 'success');
      setSelectedIncident(updated);
      await fetchIncidents(false);
    } catch (err) {
      setIncidents((prev) =>
        prev.map((inc) => {
          if (inc.event?.id === id) {
            const updated = {
              ...inc,
              human_gate: { ...inc.human_gate, status: 'APPROVED', reviewer, notes },
              action: { ...inc.action, status: 'DISPATCHED' },
            };
            setSelectedIncident(updated);
            return updated;
          }
          return inc;
        })
      );
      showNotification(`Incident ${id} APPROVED (Demo Mode). Action dispatched.`, 'success');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (id, reviewer, notes) => {
    try {
      setActionLoading(true);
      if (!backendOnline) {
        setIncidents((prev) =>
          prev.map((inc) => {
            if (inc.event?.id === id) {
              const updated = {
                ...inc,
                human_gate: { ...inc.human_gate, status: 'REJECTED', reviewer, notes },
                action: { ...inc.action, status: 'CANCELLED' },
              };
              setSelectedIncident(updated);
              return updated;
            }
            return inc;
          })
        );
        showNotification(`Incident ${id} REJECTED (Demo Mode). Action cancelled.`, 'info');
        return;
      }
      const updated = await rejectEvent(id, reviewer, notes);
      showNotification(`Incident ${id} REJECTED. Action cancelled.`, 'info');
      setSelectedIncident(updated);
      await fetchIncidents(false);
    } catch (err) {
      setIncidents((prev) =>
        prev.map((inc) => {
          if (inc.event?.id === id) {
            const updated = {
              ...inc,
              human_gate: { ...inc.human_gate, status: 'REJECTED', reviewer, notes },
              action: { ...inc.action, status: 'CANCELLED' },
            };
            setSelectedIncident(updated);
            return updated;
          }
          return inc;
        })
      );
      showNotification(`Incident ${id} REJECTED (Demo Mode). Action cancelled.`, 'info');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRequestEvidence = async (id, reviewer, notes) => {
    try {
      setActionLoading(true);
      if (!backendOnline) {
        setIncidents((prev) =>
          prev.map((inc) => {
            if (inc.event?.id === id) {
              const updated = {
                ...inc,
                human_gate: { ...inc.human_gate, status: 'REQUEST_MORE_EVIDENCE', reviewer, notes },
                action: { ...inc.action, status: 'PAUSED_AWAITING_EVIDENCE' },
              };
              setSelectedIncident(updated);
              return updated;
            }
            return inc;
          })
        );
        showNotification(`Evidence requested for incident ${id} (Demo Mode).`, 'info');
        return;
      }
      const updated = await requestMoreEvidence(id, reviewer, notes);
      showNotification(`Evidence requested for incident ${id}. Status: REQUEST_MORE_EVIDENCE`, 'info');
      setSelectedIncident(updated);
      await fetchIncidents(false);
    } catch (err) {
      setIncidents((prev) =>
        prev.map((inc) => {
          if (inc.event?.id === id) {
            const updated = {
              ...inc,
              human_gate: { ...inc.human_gate, status: 'REQUEST_MORE_EVIDENCE', reviewer, notes },
              action: { ...inc.action, status: 'PAUSED_AWAITING_EVIDENCE' },
            };
            setSelectedIncident(updated);
            return updated;
          }
          return inc;
        })
      );
      showNotification(`Evidence requested for incident ${id} (Demo Mode).`, 'info');
    } finally {
      setActionLoading(false);
    }
  };

  const handleUpdateApiUrl = (newUrl) => {
    const trimmed = (newUrl || '').trim();
    if (!trimmed) return;
    setApiBaseUrl(trimmed);
    setApiUrl(trimmed);
    setInputUrl(trimmed);
    setShowConfig(false);
    showNotification(`Connecting to API: ${trimmed}`, 'info');
    fetchIncidents(true);
  };

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <div className="header-brand">
          <div className="brand-logo">
            <svg viewBox="0 0 24 24" width="28" height="28" fill="#10b981">
              <path d="M12 2L4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3zm-1 14h2v2h-2v-2zm0-8h2v6h-2V8z"/>
            </svg>
          </div>
          <div>
            <h1 className="brand-title">EcoSentinel</h1>
            <p className="brand-subtitle">Autonomous Ecological Defense Network</p>
          </div>
        </div>

        {/* Demo Controls */}
        <div className="header-actions">
          <div className="demo-btn-group">
            <button
              className="btn btn-demo btn-land"
              onClick={handleSimulateLand}
              disabled={actionLoading}
            >
              🌲 Simulate Chainsaw
            </button>
            <button
              className="btn btn-demo btn-ocean"
              onClick={handleSimulateOcean}
              disabled={actionLoading}
            >
              ⚓ Simulate Dark Vessel
            </button>
            <button
              className="btn btn-demo btn-recurrence"
              onClick={handleSeedRecurrence}
              disabled={actionLoading}
            >
              🚨 Seed Recurrence Spike
            </button>
          </div>

          <div className="connection-group">
            <div
              className="connection-status"
              onClick={() => setShowConfig((prev) => !prev)}
              title="Click to change API endpoint"
              style={{ cursor: 'pointer' }}
            >
              <span
                className={`status-dot ${backendOnline ? 'online' : 'offline'}`}
              />
              <span className="status-text">
                {backendOnline ? 'BACKEND ONLINE' : 'DISCONNECTED'}
              </span>
              {lastUpdated && (
                <span className="last-sync">
                  {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              )}
            </div>

            <button
              className="btn-api-config-toggle"
              onClick={() => setShowConfig((prev) => !prev)}
              title="Configure API URL"
            >
              ⚙️ API
            </button>
          </div>
        </div>
      </header>

      {/* API Endpoint Config Drawer */}
      {showConfig && (
        <div className="api-config-drawer">
          <div className="api-config-content">
            <span className="api-config-label">Active Backend API:</span>
            <input
              type="text"
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              placeholder="e.g. https://ecosentinel-backend.onrender.com or http://localhost:8000"
              className="api-url-input"
            />
            <button
              className="btn-url-save"
              onClick={() => handleUpdateApiUrl(inputUrl)}
            >
              Connect
            </button>
            <button
              className="btn-quick-url"
              onClick={() => handleUpdateApiUrl('https://ecosentinel-backend.onrender.com')}
            >
              🚀 Render URL
            </button>
            <button
              className="btn-quick-url"
              onClick={() => handleUpdateApiUrl('http://localhost:8000')}
            >
              💻 Localhost:8000
            </button>
          </div>
        </div>
      )}

      {/* Notification Toast */}
      {notification && (
        <div className={`toast toast-${notification.type}`}>
          <span>{notification.message}</span>
        </div>
      )}

      {/* API Error Banner with 1-Click Reconnect */}
      {apiError && (
        <div className="error-banner">
          <div className="error-banner-text">
            ⚠️ <strong>Connection Issue:</strong> {apiError}
          </div>
          <div className="error-banner-quick-actions">
            <span>Connect to:</span>
            <button
              className="btn-quick-url"
              onClick={() => handleUpdateApiUrl('https://ecosentinel-backend.onrender.com')}
            >
              🚀 Render Backend
            </button>
            <button
              className="btn-quick-url"
              onClick={() => handleUpdateApiUrl('http://localhost:8000')}
            >
              💻 Localhost:8000
            </button>
            <input
              type="text"
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              placeholder="Custom API URL (e.g. https://...onrender.com)"
              className="api-url-input-inline"
            />
            <button
              className="btn-url-save"
              onClick={() => handleUpdateApiUrl(inputUrl)}
            >
              Save & Connect
            </button>
          </div>
        </div>
      )}

      {/* Main Grid View */}
      <main className="dashboard-grid">
        {/* Left Column: Interactive Map & Incidents */}
        <div className="left-panel">
          <MapView
            incidents={incidents}
            selectedIncident={selectedIncident}
            onSelectIncident={setSelectedIncident}
          />
          <IncidentList
            incidents={incidents}
            selectedIncident={selectedIncident}
            onSelectIncident={setSelectedIncident}
            loading={loading}
          />
        </div>

        {/* Right Column: Reasoning Dossier & Pipeline Trajectory */}
        <div className="right-panel">
          <IncidentDetails
            incident={selectedIncident}
            onApprove={handleApprove}
            onReject={handleReject}
            onRequestEvidence={handleRequestEvidence}
            actionLoading={actionLoading}
          />
          <PipelineStatus incident={selectedIncident} />
        </div>
      </main>
    </div>
  );
}
