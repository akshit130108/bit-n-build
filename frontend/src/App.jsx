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
} from './api/ecosentinel';

export default function App() {
  const [incidents, setIncidents] = useState([]);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [loading, setLoading] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [notification, setNotification] = useState(null);
  const [apiError, setApiError] = useState(null);

  const showNotification = (message, type = 'info') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4500);
  };

  // Fetch all incidents from GET /events
  const fetchIncidents = useCallback(async (isInitial = false) => {
    if (isInitial) setLoading(true);
    try {
      const data = await getEvents({ limit: 100 });
      setIncidents(data);
      setBackendOnline(true);
      setApiError(null);
      setLastUpdated(new Date());

      // Auto-select latest incident if none selected
      setSelectedIncident((prev) => {
        if (!prev && data.length > 0) return data[0];
        // Keep selected incident updated with latest state
        if (prev) {
          const updated = data.find((d) => d.event?.id === prev.event?.id);
          return updated || prev;
        }
        return prev;
      });
    } catch (err) {
      setBackendOnline(false);
      setApiError(err.message || 'Failed to connect to EcoSentinel backend');
    } finally {
      if (isInitial) setLoading(false);
    }
  }, []);

  // Poll GET /events every 3 seconds
  useEffect(() => {
    fetchIncidents(true);
    const interval = setInterval(() => {
      fetchIncidents(false);
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchIncidents]);

  // Demo Handlers
  const handleSimulateLand = async () => {
    try {
      setActionLoading(true);
      const res = await simulateLand();
      showNotification(`Simulated Chainsaw event [${res.event?.id}] processed: ${res.classification?.refined_type}`, 'success');
      await fetchIncidents(false);
      setSelectedIncident(res);
    } catch (err) {
      showNotification(`Failed to simulate land event: ${err.message}`, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSimulateOcean = async () => {
    try {
      setActionLoading(true);
      const res = await simulateOcean();
      showNotification(`Simulated Dark Vessel event [${res.event?.id}] processed: ${res.classification?.refined_type}`, 'success');
      await fetchIncidents(false);
      setSelectedIncident(res);
    } catch (err) {
      showNotification(`Failed to simulate ocean event: ${err.message}`, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSeedRecurrence = async () => {
    try {
      setActionLoading(true);
      const res = await seedRecurrence();
      const trigger = res.new_trigger_incident;
      showNotification(`Recurrence Spike Demonstrated! 3 seeded incidents caused Risk score to surge to ${trigger.risk?.score}/100`, 'warning');
      await fetchIncidents(false);
      setSelectedIncident(trigger);
    } catch (err) {
      showNotification(`Failed to seed recurrence: ${err.message}`, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // Approval Handlers
  const handleApprove = async (id, reviewer, notes) => {
    try {
      setActionLoading(true);
      const updated = await approveEvent(id, reviewer, notes);
      showNotification(`Incident ${id} APPROVED. Action dispatched: ${updated.action?.action}`, 'success');
      setSelectedIncident(updated);
      await fetchIncidents(false);
    } catch (err) {
      showNotification(`Approval failed: ${err.message}`, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (id, reviewer, notes) => {
    try {
      setActionLoading(true);
      const updated = await rejectEvent(id, reviewer, notes);
      showNotification(`Incident ${id} REJECTED. Action cancelled.`, 'info');
      setSelectedIncident(updated);
      await fetchIncidents(false);
    } catch (err) {
      showNotification(`Rejection failed: ${err.message}`, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRequestEvidence = async (id, reviewer, notes) => {
    try {
      setActionLoading(true);
      const updated = await requestMoreEvidence(id, reviewer, notes);
      showNotification(`Evidence requested for incident ${id}. Status: REQUEST_MORE_EVIDENCE`, 'info');
      setSelectedIncident(updated);
      await fetchIncidents(false);
    } catch (err) {
      showNotification(`Request evidence failed: ${err.message}`, 'error');
    } finally {
      setActionLoading(false);
    }
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

          <div className="connection-status">
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
        </div>
      </header>

      {/* Notification Toast */}
      {notification && (
        <div className={`toast toast-${notification.type}`}>
          <span>{notification.message}</span>
        </div>
      )}

      {/* API Error Banner */}
      {apiError && (
        <div className="error-banner">
          ⚠️ Connection Issue: {apiError}. Check that the backend is running on <code>http://localhost:8000</code>.
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
