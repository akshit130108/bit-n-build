import React, { useState } from 'react';
import RiskBadge from './RiskBadge';

export default function IncidentList({ incidents = [], selectedIncident, onSelectIncident, loading }) {
  const [filterDomain, setFilterDomain] = useState('ALL');

  const filtered = incidents.filter((inc) => {
    if (filterDomain === 'LAND') return inc.event?.domain === 'land';
    if (filterDomain === 'OCEAN') return inc.event?.domain === 'ocean';
    if (filterDomain === 'HIGH_RISK') return ['HIGH', 'CRITICAL'].includes(inc.risk?.level);
    return true;
  });

  return (
    <div className="incident-list-container">
      <div className="list-header">
        <div className="list-title">
          <h3>Active Incidents</h3>
          <span className="count-pill">{filtered.length} of {incidents.length}</span>
        </div>

        <div className="filter-tabs">
          {['ALL', 'LAND', 'OCEAN', 'HIGH_RISK'].map((f) => (
            <button
              key={f}
              className={`filter-btn ${filterDomain === f ? 'active' : ''}`}
              onClick={() => setFilterDomain(f)}
            >
              {f.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      <div className="incident-items">
        {loading && incidents.length === 0 ? (
          <div className="empty-state">Loading telemetry feeds...</div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">No incidents match the active filter.</div>
        ) : (
          filtered.map((inc) => {
            const isSelected = selectedIncident?.event?.id === inc.event?.id;
            const domain = inc.event?.domain || 'land';
            const eventType = inc.event?.event_type || 'Unknown';
            const riskLevel = inc.risk?.level || 'LOW';
            const riskScore = inc.risk?.score;
            const confidencePct = Math.round((inc.event?.confidence || 0) * 100);
            const status = inc.human_gate?.status || 'MONITORING';
            const isWaiting = status === 'WAITING_FOR_APPROVAL';

            const timeStr = inc.event?.timestamp
              ? new Date(inc.event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              : 'N/A';

            return (
              <div
                key={inc.event?.id || Math.random()}
                className={`incident-card ${isSelected ? 'selected' : ''} ${isWaiting ? 'waiting-pulse' : ''}`}
                onClick={() => onSelectIncident(inc)}
              >
                <div className="card-top">
                  <div className="card-title-group">
                    <span className={`domain-tag ${domain}`}>
                      {domain === 'land' ? '🌲 LAND' : '⚓ OCEAN'}
                    </span>
                    <span className="card-event-name">{eventType}</span>
                  </div>
                  <RiskBadge level={riskLevel} score={riskScore} />
                </div>

                <div className="card-mid">
                  <span className="card-action">
                    Target: <strong>{inc.action?.action || 'MONITOR'}</strong>
                  </span>
                  <span className="card-conf">{confidencePct}% conf</span>
                </div>

                <div className="card-bottom">
                  <span className="card-time">{timeStr}</span>
                  {isWaiting && (
                    <span className="waiting-tag">⚠️ WAITING APPROVAL</span>
                  )}
                  {inc.action?.dispatched && (
                    <span className="dispatched-tag">✓ DISPATCHED</span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
